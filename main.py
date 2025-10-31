"""
PROJETO DE CRIAÇÃO DO EXECUTÁVEL DE MANIPULADOR DE PDF PARA O DOSSIE DA SINTECH.
"""

import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import Toplevel, filedialog, messagebox, ttk

from funcs_pdf import func_converter_imagem_para_pdf, func_converter_pdf_imagem, func_juntar_pdfs, func_comprimir_pdf
from organizador_pdf import ReorganizerWindow
from pdf_popup import PDFPopup


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # --- Configuração da Janela Principal ---
        self.title("Gerenciador de Arquivos")
        self.geometry("800x500")  # Define um tamanho inicial
        self.popup_window = None
        # --- Criação dos Frames Principais ---
        # Frame para a barra de ferramentas (toolbar)
        toolbar_frame = tk.Frame(self, bd=1, relief=tk.RAISED)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)

        # Frame para a lista de arquivos (usando ttk para um visual melhor)
        list_frame = ttk.Frame(self)
        list_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        funcoes_frame = ttk.Frame(self, relief=tk.RAISED)
        funcoes_frame.pack(side=tk.TOP, fill=tk.X)
        # --- Barra de Ferramentas (Toolbar) ---
        button_configs = [
            {"text": "Adicionar", "command": self.selecionar_arquivos},
            {"text": "Remover", "command": self.remove_file},
            {"text": "Subir", "command": self.move_up},
            {"text": "Descer", "command": self.move_down},
            {"text": "Limpar Lista", "command": self.clear_list},
            {"text": "Visualizar arquivo", "command": self.abrir_pdf},
            {"text": "Sobre", "command": self.show_about},
        ]

        for config in button_configs:
            # Usando ttk.Button para um visual mais moderno
            button = ttk.Button(
                toolbar_frame,
                text=config["text"],
                command=config["command"],
                compound=tk.TOP,
            )
            button.pack(side=tk.LEFT, padx=5, pady=5)

        # --- Lista de Arquivos (Treeview) ---
        columns = ("file_name", "file_path")

        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        # Configurando os cabeçalhos das colunas
        self.tree.heading("file_name", text="Nome do Arquivo")
        self.tree.heading("file_path", text="Pasta do Arquivo")

        # Configurando a largura das colunas
        self.tree.column("file_name", width=200)
        self.tree.column("file_path", width=400)

        # Adicionando uma barra de rolagem
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Posicionando a lista e a barra de rolagem com o layout grid
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", self.on_treeview_double_click)
        self.tree.bind("<Button-1>", self.on_treeview_click)
        # Fazendo com que a lista se expanda com a janela
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.lista_arquivos = []

        # Agora tenho que colocar as funcoes relacionadas ao pdf, funcoes que já estão feitas.
        # adicionar os botoes:
        button_configs = [
            {"text": "Juntar arquivos", "command": self.juntar_pdfs},
            {"text": "Comprimir arquivo", "command": self.comprimir_pdf},
            {"text": "Organizar arquivo", "command": self.organizar_pdf},
            {"text": "Converter em imagem", "command": self.converter_em_imagem}
        ]

        for config in button_configs:
            button = ttk.Button(
                funcoes_frame,
                text=config["text"],
                command=config["command"],
                compound=tk.TOP,
            )
            button.pack(side=tk.LEFT, padx=5, pady=5)

        self.progress_bar = ttk.Progressbar(self, mode="indeterminate")

    # --- Funções de Comando (Callbacks) ---

    def selecionar_arquivos(self):
        arquivos = filedialog.askopenfilenames(
            title="Selecione os arquivos.",
            filetypes=(
                ("Arquivos", ["*.jpg", "*.jpeg", "*.png", "*.pdf"]),
                ("Todos os arquivos", "*.*"),
            ),
        )

        for arquivo in arquivos:
            if arquivo not in self.lista_arquivos:
                self.lista_arquivos.append(arquivo)
        self.atualizar_tree_view()

    def remove_file(self):
        selected_items = self.tree.selection()
        if not selected_items:
            print("Nenhum item selecionado para remover.")
            return

        print(f"Removendo itens: {selected_items}")
        for item in selected_items:
            indice = self.tree.index(item)
            self.lista_arquivos.pop(indice)
            self.tree.delete(item)

        for item in self.lista_arquivos:
            print(item)

    def move_up(self):
        """Move o item selecionado uma posição para cima na lista."""
        selected_items = self.tree.selection()
        todos_itens = self.tree.get_children()
        print("\n----- todos_itens:", todos_itens)
        print("\n----- selected_items:", selected_items)

        if not selected_items:
            return

        indices = sorted([self.tree.index(i) for i in selected_items])
        print("\n----- indices:", indices)
        if indices[0] == 0:
            return

        lista_novos_indices = []
        for indice in indices:
            print("\n----- indice:", indice)
            item_data = self.lista_arquivos.pop(indice)
            self.lista_arquivos.insert(indice - 1, item_data)
            new_item_id = self.tree.get_children()[indice - 1]
            lista_novos_indices.append(new_item_id)

        todos_itens = self.tree.get_children()
        print("\n----- todos_itens:", todos_itens)
        print("\n----- lista_novos_indices:", lista_novos_indices)

        novos_indices = sorted([self.tree.index(i) for i in lista_novos_indices])
        print("\n----- novos_indices:", novos_indices)

        self.atualizar_tree_view()

        for selecao in novos_indices:
            lista_itens = self.tree.get_children()
            self.tree.selection_add(lista_itens[selecao])
            print("\n----- selecoes:", self.tree.selection())

    def move_down(self):
        """Move o item selecionado uma posição para baixo na lista."""
        selected_items = self.tree.selection()
        todos_itens = self.tree.get_children()
        print("\n----- todos_itens:", todos_itens)
        print("\n----- selected_items:", selected_items)

        if not selected_items:
            return

        indices = sorted([self.tree.index(i) for i in selected_items])
        print("\n----- indices:", indices)
        if indices[-1] == len(self.lista_arquivos) - 1:
            return

        lista_novos_indices = []
        for indice in indices:
            print("\n----- indice:", indice)
            item_data = self.lista_arquivos.pop(indice)
            self.lista_arquivos.insert(indice + 1, item_data)
            new_item_id = self.tree.get_children()[indice + 1]
            lista_novos_indices.append(new_item_id)

        todos_itens = self.tree.get_children()
        print("\n----- todos_itens:", todos_itens)
        print("\n----- lista_novos_indices:", lista_novos_indices)

        novos_indices = sorted([self.tree.index(i) for i in lista_novos_indices])
        print("\n----- novos_indices:", novos_indices)

        self.atualizar_tree_view()

        for selecao in novos_indices:
            lista_itens = self.tree.get_children()
            self.tree.selection_add(lista_itens[selecao])
            print("\n----- selecoes:", self.tree.selection())

    def clear_list(self):
        print("Limpando toda a lista.")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lista_arquivos.clear()

    def show_about(self):
        print("Botão 'Sobre' clicado!")
        messagebox.showinfo("Sobre", "Aplicação Gerenciador de Arquivos\nVersão 6.0")

    def atualizar_tree_view(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for arquivo in self.lista_arquivos:
            head, tail = os.path.split(arquivo)
            self.tree.insert("", tk.END, text=tail, values=[tail, head])

    def juntar_pdfs(self):
        if len(self.lista_arquivos) <= 1:
            self.selecionar_arquivos()
            return
        conversao = {}
        for arquivo in self.lista_arquivos:
            if os.path.splitext(arquivo)[1] in [".png", ".jpg", ".jpeg"]:
                conversao[arquivo] = func_converter_imagem_para_pdf(
                    arquivo, stream=True
                )

        arquivo_saida = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("Arquivos PDF", "*.pdf"),),
            title="Salvar PDF como...",
        )
        if not arquivo_saida:
            return
        print("---- arquivo_saida: ", arquivo_saida)

        mensagem = f"Arquivo {os.path.split(arquivo_saida)[-1]} salvo com sucesso!"
        if not conversao:
            func_juntar_pdfs(self.lista_arquivos, arquivo_saida)
            messagebox.showinfo("Salvamento", mensagem)
        else:
            func_juntar_pdfs(self.lista_arquivos, arquivo_saida, conversao)
            messagebox.showinfo("Salvamento", mensagem)

    def comprimir_pdf(self):
        if not self.lista_arquivos:
            self.selecionar_arquivos()
            return
        
        self.popup_progresso = Toplevel(self) # self.master ou a referência da sua janela principal
        self.popup_progresso.title("Comprimindo...")
        
        # --- Configurações do Popup (Modal e Centralizado) ---
        self.popup_progresso.transient(self)
        self.popup_progresso.resizable(False, False)
        
        # Adiciona os widgets de feedback DENTRO do popup
        # Usamos 'self.' para que a função _processar_fila possa acessá-los
        self.label_popup_status = ttk.Label(self.popup_progresso, text="Iniciando...", anchor="w", width=50)
        self.label_popup_status.pack(pady=(10, 5), padx=10, fill="x")

        self.barra_popup_progresso = ttk.Progressbar(self.popup_progresso, orient='horizontal', length=300, mode='determinate')
        self.barra_popup_progresso.pack(pady=(0, 15), padx=10)
        self.barra_popup_progresso['maximum'] = len(self.lista_arquivos)

        # Centraliza o popup
        self.popup_progresso.update_idletasks()
        # ... (cálculo de geometria para centralizar) ...
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        main_height = self.winfo_height()
        popup_width = self.popup_progresso.winfo_width()
        popup_height = self.popup_progresso.winfo_height()
        pos_x = main_x + (main_width // 2) - (popup_width // 2)
        pos_y = main_y + (main_height // 2) - (popup_height // 2)
        self.popup_progresso.geometry(f"+{pos_x}+{pos_y}")

        self.popup_progresso.focus_set()
        self.popup_progresso.grab_set()

        # 3. CRIAR FILA E INICIAR THREAD (igual a antes)
        self.fila_feedback = queue.Queue()
        thread_conversor = threading.Thread(
            target=self._worker_compressao,
            args=(self.lista_arquivos, self.fila_feedback)
        )
        thread_conversor.daemon = True
        thread_conversor.start()

        # 4. INICIAR O VERIFICADOR (igual a antes)
        self.after(100, self._processar_fila)

    # def comprimir_pdf(self):
    #     if not self.lista_arquivos:
    #         self.selecionar_arquivos()
    #         return
    #     # self.atualizar_tree_view()
    #     for arquivo in self.lista_arquivos:
    #         nome_arquivo, ext = os.path.splitext(arquivo)
    #         if ext == ".pdf":
    #             novo_nome = f"{nome_arquivo}_compressed{ext}"
    #             print(nome_arquivo, "---", ext)
    #             try:
    #                 func_comprimir_pdf(arquivo, novo_nome)
    #                 mensagem = f"Arquivo {os.path.split(arquivo)[-1]} comprimido e salvo com sucesso!"
    #                 messagebox.showinfo("Salvamento", mensagem)
    #             except Exception as e:
    #                 mensagem = (
    #                     f"Erro a comprimir o arquivo {os.path.split(arquivo)[-1]}: {e}"
    #                 )
    #                 messagebox.showerror("Erro", mensagem)

    def abrir_pdf(self):
        """Abre a caixa de diálogo e cria a janela de pop-up para visualização."""
        selected_items = self.tree.selection()
        if not self.lista_arquivos:
            self.selecionar_arquivos()
            return
        if not selected_items:
            return
        indices = sorted([self.tree.index(i) for i in selected_items])

        filepath = self.lista_arquivos[indices[0]]
        print(filepath)

        # Se já existir um pop-up aberto, feche-o antes de abrir um novo.
        if self.popup_window and self.popup_window.winfo_exists():
            self.popup_window.on_close()

        # Cria a nova janela de pop-up
        self.popup_window = PDFPopup(self, filepath)
        self.popup_window.grab_set()  # Foca a interação no pop-up

    def on_treeview_double_click(self, event):
        """Callback para o evento de duplo clique no Treeview."""
        # Identifica o item que foi clicado
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return  # Clicou em uma área vazia

        # Pega as informações do item, incluindo os 'values'
        item = self.tree.item(item_id)
        item_caminho = item["values"]
        filepath = os.path.join(item_caminho[1], item_caminho[0])
        print("filepath", filepath)

        if self.popup_window and self.popup_window.winfo_exists():
            self.popup_window.on_close()

        # Cria a nova janela de pop-up
        self.popup_window = PDFPopup(self, filepath)
        self.popup_window.grab_set()  # Foca a interação no pop-up

    def organizar_pdf(self):
        if not self.lista_arquivos:
            filepath = filedialog.askopenfilename(
                title="Selecione um arquivo PDF", filetypes=[("Arquivos PDF", "*.pdf")]
            )
        elif self.tree.selection():
            item_selecionado = self.tree.selection()[0]
            indice = self.tree.index(item_selecionado)
            filepath = self.lista_arquivos[indice]
        else:
            filepath = next(
                (
                    arquivo
                    for arquivo in self.lista_arquivos
                    if arquivo.endswith(".pdf")
                ),
                None,
            )
        if not filepath or not filepath.endswith(".pdf"):
            return
        if self.popup_window and self.popup_window.winfo_exists():
            self.popup_window.on_close()
        self.popup_window = ReorganizerWindow(self, filepath)
        self.popup_window.grab_set()

    def converter_em_imagem(self):
        """
        Função "Gerente": Cria um popup com feedback e inicia a thread.
        """
        if not self.lista_arquivos:
            filepaths = filedialog.askopenfilenames(
                title="Selecione os arquivos PDF", filetypes=[("Arquivos PDF", "*.pdf")]
            )
            for arquivo in filepaths:
                if arquivo not in self.lista_arquivos:
                    self.lista_arquivos.append(arquivo)
            self.atualizar_tree_view()

        elif self.tree.selection():
            itens_selecionados = self.tree.selection()
            lista_selecionados = []
            for item in itens_selecionados:
                indice = self.tree.index(item)
                lista_selecionados.append(self.lista_arquivos[indice])
            filepaths = lista_selecionados
        else:
            filepaths = [
                    arquivo
                    for arquivo in self.lista_arquivos
                    if arquivo.endswith(".pdf")
                ]
            for arquivo in filepaths:
                if arquivo not in self.lista_arquivos:
                    self.lista_arquivos.append(arquivo)
            self.atualizar_tree_view()
        if not filepaths:
            return
        
        # 2. CRIAR O POPUP DE PROGRESSO
        self.popup_progresso = Toplevel(self) # self.master ou a referência da sua janela principal
        self.popup_progresso.title("Convertendo...")
        
        # --- Configurações do Popup (Modal e Centralizado) ---
        self.popup_progresso.transient(self)
        self.popup_progresso.resizable(False, False)
        
        # Adiciona os widgets de feedback DENTRO do popup
        # Usamos 'self.' para que a função _processar_fila possa acessá-los
        self.label_popup_status = ttk.Label(self.popup_progresso, text="Iniciando...", anchor="w", width=50)
        # self.label_popup_status = ttk.Label(self.popup_progresso, text=f"Processando {1}/{len(filepaths)}: {Path(self.lista_arquivos[0]).stem}", anchor="w", width=50)
        self.label_popup_status.pack(pady=(10, 5), padx=10, fill="x")

        self.barra_popup_progresso = ttk.Progressbar(self.popup_progresso, orient='horizontal', length=300, mode='determinate')
        self.barra_popup_progresso.pack(pady=(0, 15), padx=10)
        self.barra_popup_progresso['maximum'] = len(filepaths)

        # Centraliza o popup
        self.popup_progresso.update_idletasks()
        # ... (cálculo de geometria para centralizar) ...
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        main_height = self.winfo_height()
        popup_width = self.popup_progresso.winfo_width()
        popup_height = self.popup_progresso.winfo_height()
        pos_x = main_x + (main_width // 2) - (popup_width // 2)
        pos_y = main_y + (main_height // 2) - (popup_height // 2)
        self.popup_progresso.geometry(f"+{pos_x}+{pos_y}")

        self.popup_progresso.focus_set()
        self.popup_progresso.grab_set()

        # 3. CRIAR FILA E INICIAR THREAD (igual a antes)
        self.fila_feedback = queue.Queue()
        thread_conversor = threading.Thread(
            target=self._worker_conversao,
            args=(filepaths, self.fila_feedback)
        )
        thread_conversor.daemon = True
        thread_conversor.start()

        # 4. INICIAR O VERIFICADOR (igual a antes)
        self.after(100, self._processar_fila)

    def _worker_conversao(self, filepaths, fila):
        """
        Função "Trabalhadora": NENHUMA MUDANÇA NECESSÁRIA.
        Ela apenas envia relatórios para a fila, sem saber onde serão exibidos.
        """
        try:
            total_arquivos = len(filepaths)
            for i, caminho in enumerate(filepaths):
                nome_arquivo = Path(caminho).stem

                # --- MENSAGEM 1: AVISANDO QUE VAI COMEÇAR ---
                # Esta mensagem é apenas para atualizar o texto do label.
                aviso_inicio = {
                    "tipo": "iniciando_arquivo",
                    "total": total_arquivos,
                    "atual": i + 1,
                    "arquivo": nome_arquivo
                }
                fila.put(aviso_inicio)

                # --- EXECUTA A TAREFA PESADA ---
                # (A sua função de conversão real)
                func_converter_pdf_imagem(caminho)

                # --- MENSAGEM 2: AVISANDO QUE TERMINOU ---
                # Esta mensagem é para avançar a barra de progresso.
                progresso = {
                    "tipo": "progresso",
                    "atual": i + 1,
                }
                fila.put(progresso)

            # Ao final de tudo, envia a mensagem de sucesso
            fila.put({"tipo": "sucesso"})

        except Exception as e:
            # Se der erro em qualquer ponto, envia a mensagem de erro
            fila.put({"tipo": "erro", "mensagem": str(e)})

    def _worker_compressao(self, filepaths, fila):
        """
        Função "Trabalhadora": NENHUMA MUDANÇA NECESSÁRIA.
        Ela apenas envia relatórios para a fila, sem saber onde serão exibidos.
        """
        try:
            total_arquivos = len(filepaths)
            for i, caminho in enumerate(filepaths):
                nome_arquivo = Path(caminho).stem
                ext = Path(caminho).suffix

                if ext == ".pdf":
                    aviso_inicio = {
                        "tipo": "iniciando_arquivo",
                        "total": total_arquivos,
                        "atual": i + 1,
                        "arquivo": nome_arquivo
                    }
                    fila.put(aviso_inicio)
                    
                    # --- EXECUTA A TAREFA PESADA ---
                    novo_nome = f"{Path(caminho).with_suffix('')}_compressed.pdf"
                    func_comprimir_pdf(caminho, novo_nome)

                    # --- MENSAGEM 2: AVISANDO QUE TERMINOU ---
                    # Esta mensagem é para atualizar a BARRA DE PROGRESSO.
                    progresso = {
                        "tipo": "progresso",
                        "atual": i + 1,
                    }
                    fila.put(progresso)
            
            fila.put({"tipo": "sucesso"})
        except Exception as e:
            fila.put({"tipo": "erro", "mensagem": str(e)})

    def _processar_fila(self):
        """
        Função "Verificadora" (VERSÃO CORRIGIDA E ROBUSTA):
        Lê a fila e atualiza os widgets do POPUP de forma segura.
        """
        finalizar_loop = False
        try:
            while not self.fila_feedback.empty():
                mensagem = self.fila_feedback.get_nowait()

                if mensagem["tipo"] == "iniciando_arquivo":
                    # Se a mensagem é de início, APENAS atualize o texto do label.
                    status_text = f"Processando {mensagem['atual']}/{mensagem['total']}: {mensagem['arquivo']}"
                    self.label_popup_status.config(text=status_text)
                
                elif mensagem["tipo"] == "progresso":
                    # Se a mensagem é de progresso, APENAS atualize a barra.
                    self.barra_popup_progresso['value'] = mensagem['atual']

                elif mensagem["tipo"] == "sucesso":
                    self.label_popup_status.config(text="Compressão concluída com sucesso!")
                    self.barra_popup_progresso['value'] = self.barra_popup_progresso['maximum']
                    messagebox.showinfo("Sucesso", "Todos os arquivos foram comprimidos!")
                    finalizar_loop = True

                elif mensagem["tipo"] == "erro":
                    self.label_popup_status.config(text="Erro na compressão!")
                    messagebox.showerror("Erro de Compressão", mensagem["mensagem"])
                    finalizar_loop = True

        except queue.Empty:
            pass

        if finalizar_loop:
            self.popup_progresso.destroy()
        else:
            self.after(100, self._processar_fila)

    def on_treeview_click(self, event):
        """
        Chamado quando há um clique único no Treeview.
        Se o clique for em uma área vazia, a seleção é limpa.
        """
        # Identifica a linha (item) na coordenada y do clique
        item_id = self.tree.identify_row(event.y)

        # Se identify_row retornar uma string vazia, significa que
        # o clique não foi em um item.
        if not item_id:
            # `selection_set("")` é a maneira idiomática de limpar a seleção.
            self.tree.selection_set("")


# --- Execução da Aplicação ---
if __name__ == "__main__":
    app = App()
    app.mainloop()
