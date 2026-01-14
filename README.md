# Manipulador PDF - Ferramenta Desktop

> Uma suíte completa para manipulação, compressão e organização de arquivos PDF.

O **Manipulador PDF** é uma aplicação Desktop desenvolvida em Python para resolver gargalos comuns de produtividade em escritórios: a necessidade de juntar documentos, reduzir o tamanho de arquivos para envio por e-mail e reorganizar páginas visualmente, tudo em uma interface amigável e performática.

## 🖥️ Funcionalidades

### 1. Compressão Inteligente
Reduz drasticamente o tamanho de arquivos PDF através de um algoritmo personalizado que:
* Redimensiona páginas para o padrão A4.
* Reamostra e comprime imagens internas (JPEG/PNG) preservando a legibilidade.
* Executa em **background threads** para não travar a interface.

### 2. Organizador Visual (Drag & Drop Logic)
Uma interface dedicada para visualizar as páginas de um PDF como miniaturas:
* Reordenação de páginas com controles visuais.
* Seleção múltipla para exportar apenas páginas específicas ou excluir páginas indesejadas.
* Geração assíncrona de thumbnails para abertura rápida de arquivos grandes.

### 3. Conversão e Fusão (Merge)
* **Imagens para PDF:** Converte JPG/PNG em PDF, centralizando e ajustando a escala automaticamente.
* **Juntar PDFs:** Combina múltiplos arquivos em um único documento, com opção de compressão automática se o arquivo final exceder um limite (ex: 15MB).

### 4. Editor Rápido
* Visualizador integrado com opções de **Rotação** (90º/180º) e **Corte (Crop)** manual de áreas específicas da página.

## 🛠️ Stack Tecnológica

* **Linguagem:** Python 3.12+
* **Interface Gráfica (GUI):** Tkinter (com ttk para estilização moderna)
* **Manipulação de PDF:** PyMuPDF (Fitz) - Escolhido pela alta performance em renderização e manipulação de baixo nível.
* **Processamento de Imagem:** Pillow (PIL)
* **Concorrência:** `threading` e `queue` para operações não-bloqueantes.
* **Gerenciamento de Dependências:** `uv` (pyproject.toml).
* **Empacotamento:** PyInstaller (Geração de executável standalone para Windows).

## 🧠 Desafios Técnicos Resolvidos

### Concorrência e Responsividade da UI
Operações como comprimir um PDF de 50MB ou gerar miniaturas de 100 páginas são pesadas.
* *Solução:* Implementação do padrão **Producer-Consumer** com `queue`. A thread de trabalho processa o arquivo e envia atualizações de progresso para a fila, que a Thread Principal (UI) consome para atualizar a barra de progresso sem congelar a janela.

### Manipulação de Streams em Memória
Para evitar a criação de dezenas de arquivos temporários no disco durante a conversão de imagens ou reorganização.
* *Solução:* Uso extensivo de `io.BytesIO` para manipular buffers de imagem e PDF inteiramente na memória RAM, escrevendo no disco apenas o resultado final.

## 🚀 Como rodar o projeto

### Pré-requisitos
* Python 3.12 ou superior
* Gerenciador de pacotes `uv` (recomendado) ou `pip`.

### Instalação

1.  Clone o repositório:
    ```bash
    git clone https://github.com/seu-usuario/manipulador-pdf.git
    cd manipulador-pdf
    ```

2.  Instale as dependências:
    ```bash
    # Usando pip
    pip install -r requirements.txt
    
    # OU usando uv (se tiver o uv instalado)
    uv sync
    ```

3.  Execute a aplicação:
    ```bash
    python main.py
    ```

## 📦 Como Gerar o Executável (Build)

Para criar o arquivo `.exe` standalone (que não exige Python instalado na máquina do usuário), utilize o PyInstaller com o seguinte comando:

```bash
# Gera um único arquivo executável (-F) sem abrir console (-w) e com ícone personalizado
pyinstaller --noconsole --onefile --icon=pdf.ico --name="ManipuladorPDF" main.py

## 📄 Licença

Este projeto está sob a licença MIT.