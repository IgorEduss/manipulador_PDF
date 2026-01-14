import io
import math
import os
from typing import Literal

import pymupdf
from PIL import Image
from pathlib import Path


# Definindo constantes
LIMITE_INFERIOR_BYTES = 102400  # 100 KB
LIMITE_SUPERIOR_BYTES = 4194304 # 4 MB
FATOR_AJUSTE_PERCENTUAL = 0.05 # 5% de ajuste nas dimensões por iteração
MAX_ITERACOES = 100 # Limite para evitar loop infinito


def func_converter_imagem_para_pdf(
    caminho_imagem, arquivo_saida=None, stream=False
) -> None | bytes:
    """
    Converte uma ou mais imagens para um único arquivo PDF.

    Args:
        lista_imagens (str): caminho para os arquivos de imagem.
        arquivo_saida (str): O caminho para o arquivo PDF de saída.
    """
    if isinstance(caminho_imagem, bytes):
        image_bytes = caminho_imagem
        with pymupdf.open(stream=caminho_imagem, filetype="png") as img:
            rect = img[0].rect  # pic dimension
            img_largura, img_altura = rect.width, rect.height

    else:
        with pymupdf.open(caminho_imagem) as img:
            rect = img[0].rect  # pic dimension
            img_largura, img_altura = rect.width, rect.height
        with open(caminho_imagem, "rb") as f:
            image_bytes = f.read()

    largura_a4, altura_a4 = pymupdf.paper_sizes()["a4"]
    with pymupdf.open() as doc:
        page = doc.new_page()
        if img_largura > largura_a4 or img_altura > altura_a4:
            scale_x = largura_a4 / img_largura
            scale_y = altura_a4 / img_altura
            scale = min(scale_x, scale_y)

            new_w = img_largura * scale
            new_h = img_altura * scale

            x_offset, y_offset = 0, 0
            if new_h > new_w and new_h <= altura_a4:
                x_offset = (largura_a4 - new_w) / 2

            target_rect = pymupdf.Rect(
                x_offset, y_offset, x_offset + new_w, y_offset + new_h
            )

        else:
            x_offset = (largura_a4 - img_largura) / 2
            y_offset = 0

            target_rect = pymupdf.Rect(
                x_offset, y_offset, x_offset + img_largura, y_offset + img_altura
            )

        page.insert_image(target_rect, stream=image_bytes)

        if not stream:
            if arquivo_saida:
                doc.save(arquivo_saida)
            else:
                print("Tem que colocar o arquivo de saída!")
        else:
            return doc.tobytes()


def func_juntar_pdfs(
    lista_pdfs: list[str],
    arquivo_saida: str,
    conversoes_de_imagem: dict[str, bytes] | None = None,
    tamanho_arquivo_limite: int = 15,
):
    """
    Junta múltiplos arquivos PDF em um único documento.

    Args:
        lista_pdfs (list): Uma lista de caminhos para os arquivos PDF a serem unidos.
        arquivo_saida (str): O caminho para o arquivo PDF resultante.
        conversoes_de_imagem (dict[str, bytes]): Um dicionário tendo como chave o caminho
        do arquivo de imagem origianal e seu pdf equivalente em bytes.
        tamanho_arquivo_limite (int): A partir desse tamanho (em Mb), a função de compressão
        será executada automaticamente.
    """
    try:
        resultado = pymupdf.open()
        for pdf_path in lista_pdfs:
            if conversoes_de_imagem:
                if pdf_path in conversoes_de_imagem:
                    with pymupdf.open(
                        stream=conversoes_de_imagem[pdf_path], filetype="pdf"
                    ) as mfile:
                        resultado.insert_pdf(mfile)
                else:
                    with pymupdf.open(pdf_path) as mfile:
                        resultado.insert_pdf(mfile)
            else:
                with pymupdf.open(pdf_path) as mfile:
                    resultado.insert_pdf(mfile)
        resultado_bytes = resultado.tobytes()
        tamanho = len(resultado_bytes)
        limite = tamanho_arquivo_limite * 1024**2
        if tamanho > limite:
            func_comprimir_pdf(
                arquivo_entrada=resultado_bytes, arquivo_saida=arquivo_saida
            )
        else:
            resultado.save(arquivo_saida)
    finally:
        resultado.close()


def func_rodar_pdf(arquivo_entrada, arquivo_saida, angulo):
    """
    Rotaciona todas as páginas de um arquivo PDF.

    Args:
        arquivo_entrada (str): O caminho para o arquivo PDF de entrada.
        arquivo_saida (str): O caminho para o arquivo PDF de saída.
        angulo (int): O ângulo de rotação (90, 180, 270).
    """
    doc = pymupdf.open(arquivo_entrada)
    for pagina in doc:
        pagina.set_rotation(pagina.rotation + angulo)
    doc.save(arquivo_saida)
    doc.close()


def func_comprimir_pdf(
    arquivo_entrada: str | bytes,
    arquivo_saida: str,
    qualidade_imagem: int = 40,  # Padrão mais comum para um bom equilíbrio
    nivel_compresao_png: int = 8,
):
    """
    Comprime um arquivo PDF, padronizando as páginas para o formato A4 e
    reprocessando as imagens internas para reduzir o tamanho do arquivo.

    Args:
        arquivo_entrada (str | bytes): O caminho ou os bytes do PDF de entrada.
        arquivo_saida (str): O caminho para salvar o PDF comprimido.
        qualidade_imagem (int): Qualidade para imagens JPEG (1-100).
        nivel_compresao_png (int): Nível de compressão para imagens PNG (0-9).
    """
    try:
        # Abre o documento original a partir do caminho ou de bytes
        if isinstance(arquivo_entrada, bytes):
            doc_original = pymupdf.open(stream=arquivo_entrada, filetype="pdf")
        else:
            doc_original = pymupdf.open(arquivo_entrada)
    except Exception as e:
        print(f"Erro ao abrir o PDF: {e}")
        return

    # Cria um novo documento em branco para o resultado final
    doc_final = pymupdf.open()
    A4_RECT = pymupdf.paper_rect("a4")

    # Itera por cada página do documento original
    for n, page_original in enumerate(doc_original):
        print(f"Página {n + 1} de {len(doc_original)}")
        # Cria uma nova página A4 no documento final
        page_final = doc_final.new_page(width=A4_RECT.width, height=A4_RECT.height)

        # --- Etapa 1: Redimensionar e transferir conteúdo vetorialmente ---
        # Calcula o retângulo de destino para manter a proporção
        w0, h0 = page_original.rect.width, page_original.rect.height

        # Pega as dimensões da página de destino (A4)
        w1, h1 = A4_RECT.width, A4_RECT.height

        # Calcula os fatores de escala
        scale_x = w1 / w0
        scale_y = h1 / h0

        # Usa o menor fator para não distorcer a imagem
        scale = min(scale_x, scale_y)

        # Calcula as novas dimensões
        new_w = w0 * scale
        new_h = h0 * scale

        # Calcula o ponto de partida (x, y) para centralizar o conteúdo
        x_offset = (w1 - new_w) / 2
        y_offset = (h1 - new_h) / 2

        # Cria o retângulo de destino final
        target_rect = pymupdf.Rect(
            x_offset, y_offset, x_offset + new_w, y_offset + new_h
        )

        # Mostra a página original na nova página A4, redimensionando o conteúdo
        # sem rasterizar. Textos e vetores continuam sendo textos e vetores.
        page_final.show_pdf_page(
            target_rect,  # Onde desenhar na nova página
            doc_original,  # Documento de origem
            page_original.number,  # Número da página de origem
        )

        # --- Etapa 2: Comprimir as imagens na nova página ---
        images = page_final.get_images(full=True)
        for img_info in images:
            # Pula imagens "inline" que são geralmente pequenas
            if img_info[1] > 0:
                continue

            xref = img_info[0]
            try:
                base_image = doc_final.extract_image(xref)
                image_bytes = base_image["image"]

                # Usa Pillow para reprocessar a imagem
                image = Image.open(io.BytesIO(image_bytes))
                img_buffer = io.BytesIO()

                # Se a imagem tem transparência, usa PNG para preservá-la
                if image.mode in ("RGBA", "LA") or (
                    image.mode == "P" and "transparency" in image.info
                ):
                    image.save(
                        img_buffer,
                        format="PNG",
                        optimize=True,
                        compress_level=nivel_compresao_png,
                    )
                # Caso contrário, converte para RGB e usa JPEG
                else:
                    if image.mode != "RGB":
                        image = image.convert("RGB")
                    image.save(
                        img_buffer,
                        format="JPEG",
                        quality=qualidade_imagem,
                        optimize=True,
                    )

                compressed_bytes = img_buffer.getvalue()

                # Substitui a imagem original pela versão comprimida
                # O PyMuPDF v1.24+ tem um método direto para isso
                if hasattr(page_final, "replace_image"):
                    page_final.replace_image(xref, stream=compressed_bytes)
                else:  # Fallback para versões mais antigas
                    img_rect = page_final.get_image_rects(xref)[0]
                    page_final.delete_image(
                        xref
                    )  # Método mais seguro que _deleteObject
                    page_final.insert_image(img_rect, stream=compressed_bytes)

            except Exception as e:
                print(f"Não foi possível processar a imagem com xref {xref}: {e}")
                continue

    # Salva o arquivo final com otimizações
    try:
        doc_final.save(arquivo_saida, garbage=4, deflate=True, clean=True)
        print(f"🎉 Arquivo salvo com sucesso em: {arquivo_saida}")
    except Exception as e:
        print(f"Erro ao salvar o PDF final: {e}")
    finally:
        doc_original.close()
        doc_final.close()


def obter_tamanho_bytes(image_obj: Image.Image | str, format_str: Literal["PNG", "JPEG"] = "PNG") -> int:
    """Calcula o tamanho da imagem em bytes se fosse salva no formato e qualidade especificados."""
    try:
        if isinstance(image_obj, str):
            return os.path.getsize(image_obj)
        else:
            buffer = io.BytesIO()
            image_obj.save(buffer, format=format_str)
            return buffer.tell()
    except Exception as e:
        print(f"Erro ao obter tamanho da imagem: {e}")
        return 0

def ajusta_tamanho_imagem(caminho: str | io.BytesIO, nome_salvamento: str | Path, extensao: Literal["PNG", "JPEG"] = "PNG"):
    """
    Ajusta o tamanho de uma imagem para que fique entre LIMITE_INFERIOR_BYTES e LIMITE_SUPERIOR_BYTES.
    """
    if isinstance(caminho, str):
        img = Image.open(caminho)
    else: # Já é um BytesIO
        caminho.seek(0)
        img = Image.open(caminho)

    for i in range(MAX_ITERACOES):
        # Sempre obtenha o tamanho atualizado da imagem no buffer
        if i == 0 and isinstance(caminho, str):
            tamanho_atual_bytes = obter_tamanho_bytes(caminho)
        else:
            tamanho_atual_bytes = obter_tamanho_bytes(img, extensao)

        if LIMITE_INFERIOR_BYTES <= tamanho_atual_bytes <= LIMITE_SUPERIOR_BYTES:
            img.save(nome_salvamento)
            return True # Sucesso
        
        # Calcular novas dimensões
        atual_largura, atual_altura = img.size

        if tamanho_atual_bytes < LIMITE_INFERIOR_BYTES:
            # Aumentar imagem
            fator_escala = 1 + FATOR_AJUSTE_PERCENTUAL
            nova_largura = math.ceil(atual_largura * fator_escala)
            nova_altura = math.ceil(atual_altura * fator_escala)
            # print(f"  Aumentando para {nova_largura}x{nova_altura}")
        elif tamanho_atual_bytes > LIMITE_SUPERIOR_BYTES:
            # Diminuir imagem
            fator_escala = 1 - FATOR_AJUSTE_PERCENTUAL
            nova_largura = math.floor(atual_largura * fator_escala)
            nova_altura = math.floor(atual_altura * fator_escala)
            # print(f"  Diminuindo para {nova_largura}x{nova_altura}")
        
        # Redimensionar e atualizar a imagem para a próxima iteração
        img = img.resize((int(nova_largura), int(nova_altura))) # int() para garantir que sejam inteiros para resize

    # print(f"Ajuste falhou após {MAX_ITERACOES} iterações. Tamanho final: {tamanho_atual_bytes} B")
    return False # Falha ao ajustar dentro das iterações



def func_converter_pdf_imagem(
    caminho_pdf: str
) -> None:
    with pymupdf.open(caminho_pdf) as pdf:
        origem = Path(caminho_pdf).parent
        nome = Path(caminho_pdf).stem
        for i, pagina in enumerate(pdf):
            matriz_de_transformacao = pymupdf.Matrix(1.0, 1.0)
            pix = pagina.get_pixmap(matrix=matriz_de_transformacao)
            pix_pil = pix.pil_image()
            buffer = io.BytesIO()
            pix_pil.save(buffer, format='PNG')
            caminho_salvamento = origem / f"{nome}_{i+1}.png"
            ajusta_tamanho_imagem(buffer, nome_salvamento=caminho_salvamento)

