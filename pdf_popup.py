import io
import math
import os
import tkinter as tk
from copy import deepcopy
from tkinter import filedialog, messagebox

import pymupdf
from PIL import Image, ImageTk

from funcs_pdf import func_converter_imagem_para_pdf


class PDFPopup(tk.Toplevel):
    def __init__(self, master, filepath):
        super().__init__(master)
        self.title(f"Editor - {os.path.basename(filepath)}")

        # Configuração da geometria da janela
        relacao_tela_janela = 0.875
        relacao_janela_a4 = 1 / math.sqrt(2)
        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        self.nova_altura = int(altura_tela * relacao_tela_janela)
        self.nova_largura = int(self.nova_altura * relacao_janela_a4)
        pos_x = (largura_tela // 2) - (self.nova_largura // 2)
        pos_y = (altura_tela // 2) - (self.nova_altura // 2)
        self.geometry(f"{self.nova_largura}x{self.nova_altura}+{pos_x}+{pos_y}")

        # Variáveis de estado
        self.filepath = filepath
        self.file_type = "pdf" if filepath.lower().endswith(".pdf") else "image"
        self.current_page_index = 0
        self.rotations = {}
        self.pdf_page_crop: dict[int, Image.Image] = {}
        self.image_has_changed = False  # Flag para rastrear alterações na imagem
        self.image_rotations: dict[int, list] = {}
        self.image_coord_crop: dict[int, list] = {}

        # Variáveis para manipulação de imagem
        self.current_pil_image = None
        self.original_pil_image = None
        self.tk_photo_image = None

        # Variáveis de corte
        self.is_cropping = False
        self.crop_start_x = 0
        self.crop_start_y = 0
        self.crop_rectangle_id = None
        self.display_scale_factor = 1.0
        self.image_offset_x = 0
        self.image_offset_y = 0

        # Carregamento do arquivo
        if self.file_type == "pdf":
            self.doc = pymupdf.open(self.filepath)
            self.total_pages = len(self.doc)
            for i in range(self.total_pages):
                page = self.doc[i]
                if page.rotation != 0:
                    self.rotations[i] = page.rotation
        else:
            self.doc = None
            self.original_pil_image = Image.open(self.filepath)
            self.current_pil_image = self.original_pil_image.copy()
            self.total_pages = 1

        self.rotacoes_iniciais = deepcopy(self.rotations)
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Carrega a primeira página ou imagem
        self.update_page_display()

    def create_widgets(self):
        """Cria os widgets da interface."""
        self.image_canvas = tk.Canvas(self, bg="lightgray")
        self.image_canvas.pack(padx=10, pady=10, expand=True, fill="both")

        control_frame = tk.Frame(self)
        control_frame.pack(pady=10)
        edit_frame = tk.Frame(control_frame)
        edit_frame.pack(pady=(0, 5))

        self.rotate_ccw_button = tk.Button(
            edit_frame, text="Girar ↺", command=self.rotate_counter_clockwise
        )
        self.rotate_ccw_button.pack(side="left", padx=5)
        self.crop_button = tk.Button(
            edit_frame, text="Cortar", command=self.toggle_cropping
        )
        self.crop_button.pack(side="left", padx=5)
        self.reset_button = tk.Button(
            edit_frame, text="Resetar", command=self.reset_image_state
        )
        self.reset_button.pack(side="left", padx=5)
        self.rotate_cw_button = tk.Button(
            edit_frame, text="Girar ↻", command=self.rotate_clockwise
        )
        self.rotate_cw_button.pack(side="left", padx=5)

        nav_frame = tk.Frame(control_frame)
        nav_frame.pack(pady=(5, 0))
        self.prev_button = tk.Button(
            nav_frame, text="<< Anterior", command=self.prev_page
        )
        self.prev_button.pack(side="left", padx=5)
        self.page_info_label = tk.Label(nav_frame, text="")
        self.page_info_label.pack(side="left", padx=10)
        self.next_button = tk.Button(
            nav_frame, text="Próxima >>", command=self.next_page
        )
        self.next_button.pack(side="left", padx=5)

        # Eventos de mouse para corte
        self.image_canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.image_canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.image_canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        # Evento para redesenhar a imagem quando a janela é redimensionada
        self.image_canvas.bind("<Configure>", self.redraw_canvas)

    def update_page_display(self):
        """Carrega os dados da página/imagem atual e solicita o redesenho."""
        if self.file_type == "pdf":
            page = self.doc[self.current_page_index]
            rotation = self.rotations.get(self.current_page_index, 0)
            page.set_rotation(rotation)
            # Renderiza o PDF para uma imagem PIL
            self.pix = page.get_pixmap()
            croped_pages = list(self.pdf_page_crop.keys())
            if self.current_page_index not in croped_pages:
                # if not self.pdf_page_crop:
                self.current_pil_image = Image.frombytes(
                    "RGB", [self.pix.width, self.pix.height], self.pix.samples
                )
            else:
                self.current_pil_image = self.pdf_page_crop[self.current_page_index]
        # Para imagens, self.current_pil_image já está atualizado.

        self.redraw_canvas()  # Chama a função que desenha na tela
        self.page_info_label.config(
            text=f"Página {self.current_page_index + 1} de {self.total_pages}"
        )
        self.update_button_states()

    def redraw_canvas(self, event=None):
        """Redesenha a imagem atual no canvas, garantindo a centralização e proporção."""
        if not self.current_pil_image:
            return

        canvas_w = self.image_canvas.winfo_width()
        canvas_h = self.image_canvas.winfo_height()

        if canvas_w <= 1 or canvas_h <= 1:
            return

        # Cria uma cópia para redimensionar, preservando a original
        image_to_display = self.current_pil_image.copy()
        original_w, original_h = image_to_display.size

        # Redimensiona mantendo a proporção (thumbnail)
        image_to_display.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        displayed_w, displayed_h = image_to_display.size

        # Calcula o fator de escala para o corte
        if displayed_w > 0:
            self.display_scale_factor = original_w / displayed_w

        # Converte para formato Tkinter
        self.tk_photo_image = ImageTk.PhotoImage(image_to_display)

        # Limpa o canvas e desenha a nova imagem centralizada
        self.image_canvas.delete("all")
        self.image_offset_x = (canvas_w - displayed_w) / 2
        self.image_offset_y = (canvas_h - displayed_h) / 2

        self.image_canvas.create_image(
            canvas_w / 2, canvas_h / 2, anchor="center", image=self.tk_photo_image
        )

    def rotate(self, angle):
        """Função auxiliar para rotação."""
        if self.file_type == "image":
            self.current_pil_image = self.current_pil_image.rotate(angle, expand=True)
            self.image_has_changed = True
            self.redraw_canvas()
        else:
            if self.current_page_index in self.pdf_page_crop:
                self.current_pil_image = self.current_pil_image.rotate(
                    angle, expand=True
                )
                self.pdf_page_crop[self.current_page_index] = self.current_pil_image
            else:
                current_rotation = self.rotations.get(self.current_page_index, 0)
                new_rotation = (current_rotation - angle + 360) % 360
                if (
                    new_rotation == 0
                    and self.current_page_index not in self.rotacoes_iniciais
                ):
                    self.rotations.pop(self.current_page_index, None)
                else:
                    self.rotations[self.current_page_index] = new_rotation

            self.update_page_display()

    def rotate_clockwise(self):
        self.rotate(-90)

    def rotate_counter_clockwise(self):
        self.rotate(90)

    def toggle_cropping(self):
        self.is_cropping = not self.is_cropping
        cursor = "cross" if self.is_cropping else ""
        relief = "sunken" if self.is_cropping else "raised"
        text = "Cancelar Corte" if self.is_cropping else "Cortar"
        self.image_canvas.config(cursor=cursor)
        self.crop_button.config(relief=relief, text=text)
        if not self.is_cropping and self.crop_rectangle_id:
            self.image_canvas.delete(self.crop_rectangle_id)

    def on_mouse_press(self, event):
        if self.is_cropping:
            self.crop_start_x = self.image_canvas.canvasx(event.x)
            self.crop_start_y = self.image_canvas.canvasy(event.y)
            self.crop_rectangle_id = self.image_canvas.create_rectangle(
                self.crop_start_x,
                self.crop_start_y,
                self.crop_start_x,
                self.crop_start_y,
                outline="red",
                width=2,
                dash=(4, 4),
            )

    def on_mouse_drag(self, event):
        if self.is_cropping and self.crop_rectangle_id:
            cur_x, cur_y = (
                self.image_canvas.canvasx(event.x),
                self.image_canvas.canvasy(event.y),
            )
            self.image_canvas.coords(
                self.crop_rectangle_id,
                self.crop_start_x,
                self.crop_start_y,
                cur_x,
                cur_y,
            )

    def on_mouse_release(self, event):
        if self.is_cropping:
            end_x, end_y = (
                self.image_canvas.canvasx(event.x),
                self.image_canvas.canvasy(event.y),
            )
            self.toggle_cropping()  # Desativa o modo de corte visualmente

            box_on_canvas = (
                min(self.crop_start_x, end_x),
                min(self.crop_start_y, end_y),
                max(self.crop_start_x, end_x),
                max(self.crop_start_y, end_y),
            )

            box_on_image = (
                box_on_canvas[0] - self.image_offset_x,
                box_on_canvas[1] - self.image_offset_y,
                box_on_canvas[2] - self.image_offset_x,
                box_on_canvas[3] - self.image_offset_y,
            )

            final_box = tuple(
                int(coord * self.display_scale_factor) for coord in box_on_image
            )
            self.image_coord_crop[self.current_page_index] = final_box
            if final_box[2] > final_box[0] and final_box[3] > final_box[1]:
                self.current_pil_image = self.current_pil_image.crop(final_box)
                self.image_has_changed = True
                self.redraw_canvas()
            if self.file_type == "pdf":
                self.pdf_page_crop[self.current_page_index] = self.current_pil_image
                # self.image_has_changed = True
                self.update_page_display()

    def reset_image_state(self):
        if self.file_type == "image" and self.original_pil_image:
            self.current_pil_image = self.original_pil_image.copy()
            self.image_has_changed = False

        if self.file_type == "pdf":
            if self.current_page_index in self.pdf_page_crop:
                self.pdf_page_crop.pop(self.current_page_index)
                self.image_has_changed = False
            if self.rotations.get(self.current_page_index, None):
                self.rotations.pop(self.current_page_index)

        self.update_page_display()

    def on_close(self):
        pdf_changed = (
            self.file_type == "pdf"
            and self.rotations != self.rotacoes_iniciais
            or self.pdf_page_crop
        )
        if pdf_changed or self.image_has_changed:
            answer = messagebox.askyesnocancel(
                "Salvar Alterações?",
                "Deseja salvar as alterações no arquivo original?",
                parent=self,
            )
            if answer is None:
                return
            if answer:
                try:
                    if self.file_type == "pdf":
                        if self.pdf_page_crop:
                            for pagina, croped_page in self.pdf_page_crop.items():
                                buffer = io.BytesIO()
                                croped_page.save(buffer, format="png")
                                buffer.seek(0)
                                bytes_imagem = buffer.getvalue()
                                bytes_pagina = func_converter_imagem_para_pdf(
                                    bytes_imagem, stream=True
                                )
                                with pymupdf.open(
                                    stream=bytes_pagina, filetype="pdf"
                                ) as new_page:
                                    self.doc.delete_page(pagina)
                                    self.doc.insert_pdf(
                                        new_page,
                                        from_page=0,
                                        to_page=0,
                                        start_at=pagina,
                                    )

                        # Lógica de salvamento do PDF
                        for page_index, rotation_angle in self.rotations.items():
                            self.doc[page_index].set_rotation(rotation_angle)

                        temp_filepath = self.filepath + ".tmp"
                        self.doc.save(temp_filepath, garbage=4, deflate=True)
                        self.doc.close()
                        self.doc.is_closed = True
                        os.remove(self.filepath)
                        os.rename(temp_filepath, self.filepath)
                    else:  # Salvar imagem
                        self.current_pil_image.save(
                            self.filepath, quality=95, subsampling=0
                        )
                except Exception as e:
                    messagebox.showerror(
                        "Erro ao Salvar",
                        f"Não foi possível salvar o arquivo:\n{e}",
                        parent=self,
                    )
                    return
        if self.file_type == "pdf" and not self.doc.is_closed:
            self.doc.close()
        self.destroy()

    def next_page(self):
        if self.file_type == "pdf" and self.current_page_index < self.total_pages - 1:
            self.current_page_index += 1
            self.update_page_display()

    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.update_page_display()

    def update_button_states(self):
        is_pdf = self.file_type == "pdf"
        is_image = not is_pdf
        self.prev_button.config(
            state="normal" if is_pdf and self.current_page_index > 0 else "disabled"
        )
        self.next_button.config(
            state="normal"
            if is_pdf and self.current_page_index < self.total_pages - 1
            else "disabled"
        )
        # self.crop_button.config(state='normal' if is_image else 'disabled')
        # self.reset_button.config(state='normal' if is_image else 'disabled')


class PDFViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ferramenta de Arquivos")
        self.root.geometry("300x100")
        self.popup_window = None
        main_frame = tk.Frame(root)
        main_frame.pack(padx=20, pady=20, expand=True)
        self.open_button = tk.Button(
            main_frame, text="Abrir Arquivo", command=self.abrir_arquivo
        )
        self.open_button.pack()

    def abrir_arquivo(self):
        filepath = filedialog.askopenfilename(
            title="Selecione um arquivo",
            filetypes=[
                ("Arquivos Suportados", "*.pdf *.png *.jpg *.jpeg *.bmp *.gif"),
                ("Arquivos PDF", "*.pdf"),
                ("Arquivos de Imagem", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("Todos Arquivos", "*.*"),
            ],
        )
        if not filepath:
            return
        if self.popup_window and self.popup_window.winfo_exists():
            self.popup_window.on_close()
        self.popup_window = PDFPopup(self.root, filepath)
        self.popup_window.grab_set()


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFViewerApp(root)
    root.mainloop()
