"""Leitor da exportação de conversa do WhatsApp (brief 061). Função pura: sem banco, sem LLM.

Reconhece os dois formatos em português do Brasil — iPhone (`[25/10/2026, 14:03:12] Nome: texto`) e
Android (`25/10/2026 14:03 - Nome: texto`) — com ano de dois ou quatro dígitos e segundos opcionais.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime

_MARCA_DIRECAO = "‎"  # caractere invisível que o iPhone coloca no começo das linhas

_PADRAO_IPHONE = re.compile(
    r"^\[(?P<data>\d{1,2}/\d{1,2}/\d{2,4}), (?P<hora>\d{1,2}:\d{2}(?::\d{2})?)\] (?P<resto>.*)$"
)
_PADRAO_ANDROID = re.compile(
    r"^(?P<data>\d{1,2}/\d{1,2}/\d{2,4}) (?P<hora>\d{1,2}:\d{2}(?::\d{2})?) - (?P<resto>.*)$"
)

# Mídia, figurinha e mensagem apagada: descartadas mesmo tendo autor identificado.
_CONTEUDO_DESCARTADO = (
    "<mídia oculta>",
    "imagem ocultada",
    "áudio omitido",
    "figurinha omitida",
    "mensagem apagada",
    "esta mensagem foi apagada",
)


@dataclass(frozen=True)
class MensagemWhatsapp:
    autor: str
    quando: datetime
    texto: str


@dataclass(frozen=True)
class ConversaWhatsapp:
    participantes: tuple[str, ...]
    mensagens: tuple[MensagemWhatsapp, ...]


def _data_hora(data: str, hora: str) -> datetime:
    dia, mes, ano = (int(pedaco) for pedaco in data.split("/"))
    if ano < 100:
        ano += 2000
    partes_hora = [int(pedaco) for pedaco in hora.split(":")]
    while len(partes_hora) < 3:
        partes_hora.append(0)
    hora_, minuto, segundo = partes_hora
    return datetime(ano, mes, dia, hora_, minuto, segundo)


def _cabecalho(linha: str) -> tuple[str, str, str] | None:
    """(data, hora, resto) quando a linha abre uma mensagem nova; `None` quando é continuação."""
    casamento = _PADRAO_IPHONE.match(linha) or _PADRAO_ANDROID.match(linha)
    if casamento is None:
        return None
    return casamento["data"], casamento["hora"], casamento["resto"]


def _e_conteudo_descartado(texto: str) -> bool:
    minusculo = texto.strip().lower()
    return any(marca in minusculo for marca in _CONTEUDO_DESCARTADO)


def ler_conversa(texto: str) -> ConversaWhatsapp:
    """Lê o texto exportado (um `.txt`). Descarta avisos do sistema (sem "Nome: " depois da data —
    criptografia, mudança de número, ligação…), mídia, figurinha e mensagem apagada. Linha sem data
    emenda à mensagem anterior (mensagem de várias linhas)."""
    mensagens: list[MensagemWhatsapp] = []
    for linha_bruta in texto.splitlines():
        linha = linha_bruta.lstrip(_MARCA_DIRECAO)
        cabecalho = _cabecalho(linha)
        if cabecalho is None:
            if mensagens and linha.strip():
                ultima = mensagens[-1]
                mensagens[-1] = MensagemWhatsapp(ultima.autor, ultima.quando, f"{ultima.texto}\n{linha}")
            continue
        data, hora, resto = cabecalho
        if ": " not in resto:
            continue  # aviso do sistema: sem autor identificável
        autor, corpo = resto.split(": ", 1)
        if _e_conteudo_descartado(corpo):
            continue
        mensagens.append(MensagemWhatsapp(autor.strip(), _data_hora(data, hora), corpo.strip()))

    participantes = tuple(dict.fromkeys(mensagem.autor for mensagem in mensagens))
    return ConversaWhatsapp(participantes=participantes, mensagens=tuple(mensagens))


def _nome_do_txt(arquivo_zip: zipfile.ZipFile) -> str | None:
    nomes = [nome for nome in arquivo_zip.namelist() if nome.lower().endswith(".txt")]
    if not nomes:
        return None
    do_iphone = [nome for nome in nomes if nome.rsplit("/", 1)[-1].lower() == "_chat.txt"]
    return do_iphone[0] if do_iphone else nomes[0]


def ler_zip(dados: bytes) -> str:
    """Lê, na memória, o `.txt` da conversa dentro do `.zip` exportado; ignora fotos, áudios e outros
    arquivos do zip. Nada é gravado em disco."""
    with zipfile.ZipFile(io.BytesIO(dados)) as arquivo_zip:
        nome = _nome_do_txt(arquivo_zip)
        if nome is None:
            raise ValueError("zip sem arquivo de texto da conversa")
        return arquivo_zip.read(nome).decode("utf-8", errors="replace")


def ler_arquivo(nome: str, dados: bytes) -> ConversaWhatsapp:
    """Lê o `.zip` como veio ou o `.txt` de dentro dele; nada do arquivo enviado é gravado (brief 061)."""
    texto = ler_zip(dados) if nome.lower().endswith(".zip") else dados.decode("utf-8", errors="replace")
    return ler_conversa(texto)
