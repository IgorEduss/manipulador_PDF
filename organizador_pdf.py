import os
import threading
import tkinter as tk
from tkinter import (
    Button,
    Canvas,
    Frame,
    Label,
    Scrollbar,
    StringVar,
    Toplevel,
    filedialog,
    simpledialog,
    ttk,
)
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import showinfo

import pymupdf
from PIL import Image, ImageTk

# --- Constantes para facilitar a configuração ---
THUMBNAIL_WIDTH = 120
THUMBNAIL_HEIGHT = int(THUMBNAIL_WIDTH * (297 / 210))  # Proporção A4
BACKGROUND_COLOR = "#333333"
THUMBNAIL_BG_COLOR = "#444444"
SELECTION_COLOR = "#0078D7"
GRID_COLUMNS = 5


class ReorganizerWindow(Toplevel):
    def __init__(self, parent, pdf_path):
        super().__init__(parent)
        self.title("Reorganizar Páginas do PDF")
        self.geometry("710x796")  # Um pouco mais de altura para os novos controles

        # --- Estrutura de Dados ---
        self.pdf_path = pdf_path
        self.doc = pymupdf.open(pdf_path)
        self.page_order = list(range(self.doc.page_count))
        self.original_page_order = list(self.page_order)
        self.selected_positions = []
        self.last_clicked_pos = None
        self.thumbnail_widgets = []
        self.pil_images = []
        self.tk_images = []

        # --- NOVO: Variável para controlar o seletor de exportação ---
        self.export_option = StringVar(value="selected_only")

        self._setup_ui()

        self.loading_label.pack(pady=20)
        threading.Thread(target=self._generate_thumbnails, daemon=True).start()

    def _setup_ui(self):
        # Frame principal que conterá o Canvas e a Scrollbar
        canvas_frame = Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = Canvas(canvas_frame, highlightthickness=0)
        scrollbar = Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.thumbnail_container = Frame(self.canvas)

        # --- CORREÇÃO DO ALINHAMENTO ---
        # Usando anchor="n" (norte/topo) para que a centralização horizontal funcione corretamente.
        self.canvas_window_item = self.canvas.create_window(
            (0, 0), window=self.thumbnail_container, anchor="ne"
        )

        self.thumbnail_container.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._center_frame_in_canvas)

        # Painel de Controle de Movimento
        controls_frame = Frame(self)
        controls_frame.pack(fill=tk.X, pady=5)
        # (Botões de movimento permanecem os mesmos)
        self.btn_to_start = Button(
            controls_frame,
            text="↑↑ Início",
            command=lambda: self._move_selection("start"),
            state="disabled",
        )
        self.btn_up = Button(
            controls_frame,
            text="↑ Cima",
            command=lambda: self._move_selection("up"),
            state="disabled",
        )
        self.btn_down = Button(
            controls_frame,
            text="↓ Baixo",
            command=lambda: self._move_selection("down"),
            state="disabled",
        )
        self.btn_to_end = Button(
            controls_frame,
            text="↓↓ Fim",
            command=lambda: self._move_selection("end"),
            state="disabled",
        )
        self.btn_move_to = Button(
            controls_frame,
            text="Mover Para...",
            command=self._move_selection_to_position,
            state="disabled",
        )
        self.btn_move_to.pack(side=tk.LEFT, padx=10, expand=True)
        self.btn_to_start.pack(side=tk.LEFT, padx=5, expand=True)
        self.btn_up.pack(side=tk.LEFT, padx=5, expand=True)
        self.btn_down.pack(side=tk.LEFT, padx=5, expand=True)
        self.btn_to_end.pack(side=tk.LEFT, padx=5, expand=True)

        # --- NOVO PAINEL DE EXPORTAÇÃO ---
        # Usando um Labelframe para agrupar visualmente a nova funcionalidade
        self.export_labelframe = ttk.Labelframe(
            self, text=" Exportar a Partir da Seleção "
        )
        self.export_labelframe.pack(fill="x", padx=10, pady=5)

        export_radio_frame = Frame(self.export_labelframe)
        export_radio_frame.pack(side="left", padx=10, pady=5, expand=True)

        self.radio_selected_only = ttk.Radiobutton(
            export_radio_frame,
            text="Salvar APENAS as páginas selecionadas",
            variable=self.export_option,
            value="selected_only",
        )
        self.radio_selected_only.pack(anchor="w")

        self.radio_exclude_selected = ttk.Radiobutton(
            export_radio_frame,
            text="Salvar TUDO, EXCETO as páginas selecionadas",
            variable=self.export_option,
            value="exclude_selected",
        )
        self.radio_exclude_selected.pack(anchor="w")

        self.btn_execute_export = Button(
            self.export_labelframe,
            text="Exportar...",
            command=self._execute_export,
            bg="#17A2B8",
            fg="white",
        )
        self.btn_execute_export.pack(side="right", padx=10, pady=5)

        # Painel de Ações Finais
        actions_frame = Frame(self)
        actions_frame.pack(fill=tk.X, pady=10)

        # FUNCIONALIDADE ORIGINAL PERMANECE INTACTA
        Button(
            actions_frame,
            text="Salvar com a Nova Ordem",
            command=self._apply_and_save,
            bg="#007bff",
            fg="white",
        ).pack(side=tk.RIGHT, padx=10)
        Button(
            actions_frame,
            text="Desfazer Alterações",
            command=self._reset_to_original_order,
        ).pack(side=tk.RIGHT, padx=5)
        Button(actions_frame, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT)

        self.loading_label = Label(
            self.thumbnail_container,
            text="Carregando miniaturas...",
            font=("Arial", 16),
        )
        self.bind_all("<MouseWheel>", self._on_mousewheel)

        # Desabilita o painel de exportação inicialmente
        self._update_button_states()

    def _center_frame_in_canvas(self, event):
        canvas_width = event.width
        self.canvas.coords(self.canvas_window_item, canvas_width // 2, 0)

    def _update_button_states(self):
        move_state = "normal" if self.selected_positions else "disabled"

        # Atualiza botões de movimento
        self.btn_to_start.config(state=move_state)
        self.btn_up.config(state=move_state)
        self.btn_down.config(state=move_state)
        self.btn_to_end.config(state=move_state)
        self.btn_move_to.config(state=move_state)

        # --- NOVO: Atualiza o estado do painel de exportação ---
        # Itera sobre os widgets dentro do Labelframe e os habilita/desabilita
        for widget in self.export_labelframe.winfo_children():
            # O Frame interno precisa ser percorrido também
            if isinstance(widget, Frame):
                for sub_widget in widget.winfo_children():
                    sub_widget.configure(state=move_state)
            else:
                widget.configure(state=move_state)

        # Regras específicas para desabilitar botões de movimento
        if 0 in self.selected_positions:
            self.btn_to_start.config(state="disabled")
            self.btn_up.config(state="disabled")
        if len(self.page_order) - 1 in self.selected_positions:
            self.btn_down.config(state="disabled")
            self.btn_to_end.config(state="disabled")

    def _apply_and_save(self):
        """FUNCIONALIDADE ORIGINAL: Salva o PDF completo com a nova ordem."""
        file_path = asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Salvar PDF Reorganizado",
            initialfile=f"{os.path.splitext(os.path.basename(self.pdf_path))[0]}_reorganizado.pdf",
        )
        if not file_path:
            return

        try:
            doc_copy = pymupdf.open(self.pdf_path)
            doc_copy.select(self.page_order)
            doc_copy.save(file_path, garbage=4, deflate=True)
            doc_copy.close()
            showinfo(
                "Sucesso",
                f"O arquivo foi salvo com sucesso em:\n{file_path}",
                parent=self,
            )
        except Exception as e:
            showinfo("Erro", f"Ocorreu um erro ao salvar o arquivo:\n{e}", parent=self)

    def _execute_export(self):
        """NOVA FUNCIONALIDADE: Exporta um novo PDF baseado na seleção e no seletor."""
        export_option = self.export_option.get()

        file_path = asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Exportar Páginas Selecionadas",
            initialfile=f"{os.path.splitext(os.path.basename(self.pdf_path))[0]}_exportado.pdf",
        )
        if not file_path:
            return

        pages_to_keep = []
        if export_option == "selected_only":
            sorted_positions = sorted(self.selected_positions)
            pages_to_keep = [self.page_order[pos] for pos in sorted_positions]
        elif export_option == "exclude_selected":
            indices_to_exclude = {
                self.page_order[pos] for pos in self.selected_positions
            }
            pages_to_keep = [
                p_idx for p_idx in self.page_order if p_idx not in indices_to_exclude
            ]

        if not pages_to_keep:
            showinfo(
                "Aviso",
                "A seleção resultou em um PDF sem páginas. A operação foi cancelada.",
                parent=self,
            )
            return

        try:
            doc_copy = pymupdf.open(self.pdf_path)
            doc_copy.select(pages_to_keep)
            doc_copy.save(file_path, garbage=4, deflate=True)
            doc_copy.close()
            showinfo(
                "Sucesso",
                f"O arquivo foi exportado com sucesso em:\n{file_path}",
                parent=self,
            )
        except Exception as e:
            showinfo(
                "Erro", f"Ocorreu um erro ao exportar o arquivo:\n{e}", parent=self
            )

    # --- Funções não modificadas (omitidas para brevidade, mas devem permanecer no seu código) ---

    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _generate_thumbnails(self):
        for i in range(self.doc.page_count):
            page = self.doc.load_page(i)
            pil_img = self._create_padded_thumbnail(page)
            self.pil_images.append(pil_img)
        self.after(0, self._draw_grid)

    def _create_padded_thumbnail(self, page: pymupdf.Page, dpi=72):
        img_matrix = pymupdf.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=img_matrix)
        pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pil_img.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)
        padded_img = Image.new(
            "RGB", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), THUMBNAIL_BG_COLOR
        )
        paste_pos = (
            (THUMBNAIL_WIDTH - pil_img.width) // 2,
            (THUMBNAIL_HEIGHT - pil_img.height) // 2,
        )
        padded_img.paste(pil_img, paste_pos)
        return padded_img

    def _draw_grid(self):
        self.loading_label.destroy()
        for widget in self.thumbnail_container.winfo_children():
            widget.destroy()
        self.tk_images.clear()
        self.thumbnail_widgets.clear()
        for position, original_page_index in enumerate(self.page_order):
            pil_image = self.pil_images[original_page_index]
            tk_image = ImageTk.PhotoImage(pil_image)
            self.tk_images.append(tk_image)
            thumb_frame = Frame(
                self.thumbnail_container, bg=THUMBNAIL_BG_COLOR, cursor="hand2"
            )
            img_label = Label(thumb_frame, image=tk_image, bg=THUMBNAIL_BG_COLOR)
            img_label.pack()
            num_label = Label(
                thumb_frame,
                text=f"Pág. {original_page_index + 1}",
                bg=THUMBNAIL_BG_COLOR,
                fg="white",
            )
            num_label.pack(pady=2)
            for widget in [thumb_frame, img_label, num_label]:
                widget.bind(
                    "<Button-1>",
                    lambda e, pos=position: self._on_thumbnail_click(e, pos),
                )
                widget.bind(
                    "<Double-Button-1>",
                    lambda e, p_idx=original_page_index: self._show_page_preview(p_idx),
                )
            row, col = divmod(position, GRID_COLUMNS)
            thumb_frame.grid(row=row, column=col, padx=5, pady=5)
            self.thumbnail_widgets.append(thumb_frame)
        if self.selected_positions:
            self._update_selection_visual()

    def _on_thumbnail_click(self, event, position):
        if event.state & 1 and self.last_clicked_pos is not None:
            start, end = (
                min(self.last_clicked_pos, position),
                max(self.last_clicked_pos, position),
            )
            self.selected_positions = list(range(start, end + 1))
        elif event.state & 4:
            if position in self.selected_positions:
                self.selected_positions.remove(position)
            else:
                self.selected_positions.append(position)
            self.last_clicked_pos = position
        else:
            self.selected_positions = [position]
            self.last_clicked_pos = position
        self._update_selection_visual()
        self._update_button_states()

    def _update_selection_visual(self):
        for i, widget in enumerate(self.thumbnail_widgets):
            color = (
                SELECTION_COLOR if i in self.selected_positions else THUMBNAIL_BG_COLOR
            )
            for child in widget.winfo_children():
                child.configure(bg=color)
            widget.configure(bg=color)

    def _move_selection(self, direction):
        if not self.selected_positions:
            return
        positions_to_move = sorted(self.selected_positions)
        pages_to_move = [self.page_order[p] for p in positions_to_move]
        for pos in reversed(positions_to_move):
            self.page_order.pop(pos)
        if direction == "up":
            new_insert_pos = max(0, positions_to_move[0] - 1)
        elif direction == "down":
            new_insert_pos = min(len(self.page_order), positions_to_move[0] + 1)
        elif direction == "start":
            new_insert_pos = 0
        elif direction == "end":
            new_insert_pos = len(self.page_order)
        else:
            return
        for i, page in enumerate(pages_to_move):
            self.page_order.insert(new_insert_pos + i, page)
        self.selected_positions = list(
            range(new_insert_pos, new_insert_pos + len(pages_to_move))
        )
        self.last_clicked_pos = self.selected_positions[-1]
        self._draw_grid()
        self._update_button_states()

    def _show_page_preview(self, original_page_index):
        popup = Toplevel(self)
        popup.title(f"Visualizando Página {original_page_index + 1}")
        popup.configure(bg="black")
        popup.transient(self)
        popup.grab_set()
        screen_width, screen_height = (
            self.winfo_screenwidth(),
            self.winfo_screenheight(),
        )
        popup_height = int(screen_height * 0.90)
        page = self.doc.load_page(original_page_index)
        zoom = 2
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        high_res_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_ratio = high_res_img.width / high_res_img.height
        popup_width = int(popup_height * img_ratio)
        if popup_width > screen_width * 0.95:
            popup_width = int(screen_width * 0.95)
            popup_height = int(popup_width / img_ratio)
        pos_x, pos_y = (
            (screen_width // 2) - (popup_width // 2),
            (screen_height // 2) - (popup_height // 2),
        )
        popup.geometry(f"{popup_width}x{popup_height}+{pos_x}+{pos_y}")
        high_res_img.thumbnail((popup_width, popup_height), Image.Resampling.LANCZOS)
        tk_image = ImageTk.PhotoImage(high_res_img)
        label = Label(popup, image=tk_image, bg="black")
        label.image = tk_image
        label.pack(expand=True, fill=tk.BOTH)
        popup.bind("<Escape>", lambda e: popup.destroy())

    def _reset_to_original_order(self):
        self.page_order = self.original_page_order.copy()
        self.selected_positions = []
        self.last_clicked_pos = None
        self._draw_grid()
        self._update_button_states()

    def _move_selection_to_position(self):
        if not self.selected_positions:
            return
        target_pos = simpledialog.askinteger(
            "Mover Para Posição",
            f"Digite a nova posição (1 a {self.doc.page_count}):",
            parent=self,
            minvalue=1,
            maxvalue=self.doc.page_count,
        )
        if target_pos is None:
            return
        target_index = target_pos - 1
        positions_to_move = sorted(self.selected_positions)
        if target_index in positions_to_move:
            showinfo(
                "Movimento Inválido",
                "Você não pode mover as páginas para uma posição que já está selecionada.",
                parent=self,
            )
            return
        pages_to_move = [self.page_order[p] for p in positions_to_move]
        for pos in reversed(positions_to_move):
            self.page_order.pop(pos)
        adjustment = sum(1 for pos in positions_to_move if pos < target_index)
        new_insert_pos = target_index - adjustment
        for i, page in enumerate(pages_to_move):
            self.page_order.insert(new_insert_pos + i, page)
        self.selected_positions = list(
            range(new_insert_pos, new_insert_pos + len(pages_to_move))
        )
        self.last_clicked_pos = self.selected_positions[-1]
        self._draw_grid()
        self._update_button_states()


class PDFViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ferramenta PDF")
        self.geometry("300x100")
        self.popup_window = None
        main_frame = Frame(self)
        main_frame.pack(padx=20, pady=20, expand=True)
        open_button = Button(
            main_frame, text="Abrir PDF para Reorganizar", command=self.abrir_pdf
        )
        open_button.pack()

    def abrir_pdf(self):
        filepath = filedialog.askopenfilename(
            title="Selecione um arquivo PDF", filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not filepath:
            return
        self.popup_window = ReorganizerWindow(self, filepath)
        self.popup_window.grab_set()


if __name__ == "__main__":
    app = PDFViewerApp()
    app.mainloop()
