#!/usr/bin/env python3
"""verificar_auditoria_texto.py — confere o relatório de auditoria de "texto por inteiro" (brief 079).

Uso: scripts/verificar_auditoria_texto.py [--raiz <pasta>] [--relatorio <arquivo>] [--varredura]

O princípio auditado é do dono do projeto: quando o programa **analisa** um texto, analisa o texto
inteiro; cortar só é aceitável com exceção aprovada por Sidarta, registrada em
`docs/EXCECOES_TEXTO_INTEGRAL.md`. Este script **não julga** se um corte é aceitável — isso é de
Sidarta, lendo os pontos. Ele confere que nada ficou fora do relatório:

1. todo arquivo do universo (item 3.7 do brief) aparece na tabela de certificação, exatamente uma vez;
2. a contagem `linhas lidas/total` bate com o arquivo no disco, e `lidas < total` só com `NÃO CONFERIDO`;
3. `CERTIFICADO` tem linha de evidência; `CORTA` e `NÃO ANALÍTICO` citam um ponto que existe;
4. cada ponto tem todos os campos obrigatórios e um estado válido;
5. `EXCEÇÃO APROVADA` só vale com a linha correspondente no registro de exceções;
6. cada ocorrência da varredura mecânica aparece citada no relatório (`arquivo:linha`), com destino.

Saída: um resumo e o código 0 (coerente), 1 (inconsistência) ou 2 (coerente, com `NÃO CONFERIDO`).
Com `--varredura`, imprime `arquivo:linha<TAB>rótulo<TAB>linha de código` de cada ocorrência e sai 0 —
é dessa saída que o apêndice A do relatório é escrito.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------------------
# Universo (item 3.7 do brief): o que "todos os códigos" quer dizer
# --------------------------------------------------------------------------------------

PASTAS_IGNORADAS = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "dados",
        "logs",
        "docs",
    }
)

EXTENSOES_POR_PASTA: dict[str, tuple[str, ...]] = {
    # `agente_nw/**/*.yaml` e os `.json` da extensão vão além da letra do item 3.7 de propósito:
    # `nucleo/prompts/exemplos_conversavel.yaml` é dado de prompt e `extensao/manifest.json` é o
    # manifesto citado no próprio item. Cobrir mais do que o brief manda nunca cobre menos.
    "agente_nw": (".py", ".yaml"),
    "config": (".py", ".yaml"),
    "scripts": (".py", ".sh", ".sql"),
    "extensao": (".js", ".json"),
    "tests": (".py",),
}

RESULTADOS = ("CERTIFICADO", "CORTA", "NÃO ANALÍTICO", "NÃO CONFERIDO")

ESTADO_ABERTO = "AGUARDANDO DECISÃO DE SIDARTA"
ESTADO_APROVADO = "EXCEÇÃO APROVADA"

CAMPOS_DO_PONTO = (
    "Classe",
    "O que é cortado e quanto",
    "Qual decisão do produto depende desse corte",
    "Commit que introduziu",
    "Justificativa existente",
    "Proposta do executor",
    "Estado",
)
CAMPOS_DO_NAO_ANALITICO = (
    "Classe",
    "O que é cortado e quanto",
    "Prova de que não entra em decisão",
)

# Os padrões do passo 3 do brief, aplicados a todo arquivo do universo (um padrão de JavaScript não
# casa num .py, e um `LIMIT` dentro de uma string de Python casa — é o que se quer).
PADROES_VARREDURA: tuple[tuple[str, str], ...] = (
    ("py:slice_aberta", r"\[\s*:\s*[A-Za-z0-9_.]+\s*\]"),
    ("py:slice_cauda", r"\[\s*-\s*\d+\s*:\s*\]"),
    ("py:slice_faixa", r"\[\s*\d+\s*:\s*\d+\s*\]"),
    ("py:slice_inicio", r"\[\s*\d+\s*:\s*\]"),
    ("max_len", r"max_chars|max_len|maxlen|max_tokens"),
    ("janela", r"num_predict|num_ctx"),
    # `trunca` em vez do `truncat` do brief: pega também "truncar"/"truncada", que é como o
    # projeto escreve (`listas.py`), sem deixar de pegar "truncate"/"truncation".
    ("truncar", r"trunca|cortar|shorten|resum"),
    ("iter_parcial", r"islice|fetchmany|random\.sample|\.head\(|\.read\([^)]"),
    ("limite_sql", r"LIMIT|OFFSET|limit=|limite|maximo|máximo|top_k|n_results"),
    ("linhas", r"splitlines\(\)\[|\.split\([^)]*\)\[|\.split\(\"\\n\"\)"),
    ("coleta", r"trafilatura|chunk|sample"),
    ("colecao", r"trocas|meses|blocos|trecho"),
    ("js_corte", r"\.slice\(|\.substring\(|\.substr\(|innerText|textContent"),
)

_LINHA_TABELA = re.compile(r"^\|(?P<celulas>.+)\|\s*$")
_CONTAGEM = re.compile(r"^(?P<lidas>\d+)\s*/\s*(?P<total>\d+)$")
_TITULO_PONTO = re.compile(r"^#{2,6}\s+(?P<id>[A-Za-z][A-Za-z0-9]*-\d+)\s*(?P<resto>.*)$")
_CAMPO_PONTO = re.compile(r"^[-*]\s+(?P<rotulo>[^:]{3,80}):\s*(?P<valor>.*)$")
_ARQUIVO_LINHA = re.compile(r"[\w./-]+\.(?:py|js|json|yaml|sh|sql):\d+")
_APROVACAO = re.compile(r"Aprovado por Sidarta em \d{4}-\d{2}-\d{2}")
_VAZIO = frozenset({"", "—", "-", "–", "(vazio)", "nenhum", "n/a"})


@dataclass(frozen=True)
class Ocorrencia:
    arquivo: str
    linha: int
    rotulo: str
    codigo: str


@dataclass(frozen=True)
class LinhaCertificacao:
    arquivo: str
    lidas: int
    total: int
    resultado: str
    evidencia: str
    pontos: tuple[str, ...]


@dataclass
class Ponto:
    identificador: str
    titulo: str
    campos: dict[str, str]


def _normalizar(texto: str) -> str:
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn").strip().casefold()


def enumerar_universo(raiz: Path) -> list[str]:
    """Os arquivos de código do projeto, em caminho relativo, ordenados."""
    encontrados: set[str] = set()
    for arquivo in raiz.glob("*.py"):
        if arquivo.is_file():
            encontrados.add(arquivo.name)
    for pasta, extensoes in EXTENSOES_POR_PASTA.items():
        base = raiz / pasta
        if not base.is_dir():
            continue
        for arquivo in base.rglob("*"):
            if not arquivo.is_file() or arquivo.suffix not in extensoes:
                continue
            partes = arquivo.relative_to(raiz).parts
            if any(parte in PASTAS_IGNORADAS for parte in partes):
                continue
            encontrados.add("/".join(partes))
    return sorted(encontrados)


def contar_linhas(caminho: Path) -> int:
    return len(caminho.read_text(encoding="utf-8", errors="replace").splitlines())


def varrer(raiz: Path, universo: list[str]) -> list[Ocorrencia]:
    compilados = [(rotulo, re.compile(padrao)) for rotulo, padrao in PADROES_VARREDURA]
    ocorrencias: list[Ocorrencia] = []
    for relativo in universo:
        texto = (raiz / relativo).read_text(encoding="utf-8", errors="replace")
        for numero, linha in enumerate(texto.splitlines(), start=1):
            for rotulo, padrao in compilados:
                if padrao.search(linha):
                    ocorrencias.append(Ocorrencia(relativo, numero, rotulo, linha.strip()))
    return ocorrencias


def _celulas(linha: str) -> list[str] | None:
    achado = _LINHA_TABELA.match(linha)
    if achado is None:
        return None
    return [celula.strip() for celula in achado.group("celulas").split("|")]


def ler_certificacao(texto_relatorio: str) -> tuple[list[LinhaCertificacao], list[str]]:
    """As linhas da tabela de certificação: as de 5 células cuja segunda é `lidas/total`."""
    linhas: list[LinhaCertificacao] = []
    erros: list[str] = []
    for linha in texto_relatorio.splitlines():
        celulas = _celulas(linha)
        if celulas is None or len(celulas) != 5:
            continue
        contagem = _CONTAGEM.match(celulas[1])
        if contagem is None:
            continue
        resultado = " ".join(celulas[2].split())
        if resultado.upper() not in {r.upper() for r in RESULTADOS}:
            erros.append(f"resultado desconhecido na tabela de certificação: {celulas[0]} → {resultado!r}")
            continue
        pontos = tuple(
            parte.strip()
            for parte in re.split(r"[,;]", celulas[4])
            if parte.strip() and _normalizar(parte) not in _VAZIO
        )
        linhas.append(
            LinhaCertificacao(
                arquivo=celulas[0].strip("` "),
                lidas=int(contagem.group("lidas")),
                total=int(contagem.group("total")),
                resultado=resultado.upper(),
                evidencia=celulas[3],
                pontos=pontos,
            )
        )
    return linhas, erros


def ler_pontos(texto_relatorio: str) -> dict[str, Ponto]:
    pontos: dict[str, Ponto] = {}
    atual: Ponto | None = None
    for linha in texto_relatorio.splitlines():
        titulo = _TITULO_PONTO.match(linha)
        if titulo is not None:
            atual = Ponto(titulo.group("id"), titulo.group("resto"), {})
            pontos[atual.identificador] = atual
            continue
        if linha.startswith("#"):
            atual = None
            continue
        if atual is None:
            continue
        campo = _CAMPO_PONTO.match(linha)
        if campo is not None:
            atual.campos[_normalizar(campo.group("rotulo"))] = campo.group("valor").strip()
    return pontos


def _campo(ponto: Ponto, rotulo: str) -> str | None:
    alvo = _normalizar(rotulo)
    for chave, valor in ponto.campos.items():
        if chave == alvo or chave.startswith(alvo):
            return valor
    return None


def _conferir_ponto(ponto: Ponto, texto_excecoes: str) -> list[str]:
    erros: list[str] = []
    if _ARQUIVO_LINHA.search(ponto.titulo) is None:
        erros.append(f"ponto {ponto.identificador}: o título não traz `arquivo:linha`")

    classe = (_campo(ponto, "Classe") or "").strip().upper()
    obrigatorios = CAMPOS_DO_NAO_ANALITICO if classe == "NA" else CAMPOS_DO_PONTO
    for rotulo in obrigatorios:
        valor = _campo(ponto, rotulo)
        if valor is None:
            erros.append(f"ponto {ponto.identificador}: falta o campo obrigatório {rotulo!r}")
        elif _normalizar(valor) in _VAZIO and rotulo != "Justificativa existente":
            erros.append(f"ponto {ponto.identificador}: o campo {rotulo!r} está vazio")

    if classe == "NA":
        return erros

    estado = (_campo(ponto, "Estado") or "").strip()
    if _normalizar(estado) == _normalizar(ESTADO_APROVADO):
        aprovada = any(
            ponto.identificador in linha and _APROVACAO.search(linha) is not None
            for linha in texto_excecoes.splitlines()
        )
        if not aprovada:
            erros.append(
                f"ponto {ponto.identificador}: estado {ESTADO_APROVADO!r} sem linha correspondente no "
                "registro de exceções (docs/EXCECOES_TEXTO_INTEGRAL.md) com "
                '"Aprovado por Sidarta em AAAA-MM-DD"'
            )
    elif _normalizar(estado) != _normalizar(ESTADO_ABERTO):
        erros.append(
            f"ponto {ponto.identificador}: estado {estado!r} não é {ESTADO_ABERTO!r} nem {ESTADO_APROVADO!r}"
        )
    return erros


def _conferir_citacoes(ocorrencias: list[Ocorrencia], texto_relatorio: str) -> list[str]:
    erros: list[str] = []
    citados = {
        f"{achado.group(0)}"
        for achado in re.finditer(r"[\w./-]+\.(?:py|js|json|yaml|sh|sql):\d+(?!\d)", texto_relatorio)
    }
    for ocorrencia in sorted({(o.arquivo, o.linha, o.rotulo) for o in ocorrencias}):
        arquivo, linha, rotulo = ocorrencia
        if f"{arquivo}:{linha}" not in citados:
            erros.append(
                f"ocorrência sem destino no relatório: {arquivo}:{linha} [{rotulo}] — "
                "cite-a na seção 3, na seção 4 ou no apêndice A"
            )
    return erros


def verificar(raiz: Path, caminho_relatorio: Path, caminho_excecoes: Path) -> tuple[int, list[str]]:
    saida: list[str] = []
    erros: list[str] = []

    universo = enumerar_universo(raiz)
    texto_relatorio = caminho_relatorio.read_text(encoding="utf-8")
    texto_excecoes = caminho_excecoes.read_text(encoding="utf-8") if caminho_excecoes.exists() else ""

    linhas, erros_tabela = ler_certificacao(texto_relatorio)
    erros.extend(erros_tabela)
    pontos = ler_pontos(texto_relatorio)

    por_arquivo: dict[str, list[LinhaCertificacao]] = {}
    for linha in linhas:
        por_arquivo.setdefault(linha.arquivo, []).append(linha)

    for arquivo in sorted(set(por_arquivo) - set(universo)):
        erros.append(f"na tabela mas fora do universo (ou inexistente): {arquivo}")
    for arquivo in universo:
        if arquivo not in por_arquivo:
            erros.append(f"arquivo do universo ausente da tabela de certificação: {arquivo}")
        elif len(por_arquivo[arquivo]) > 1:
            erros.append(f"arquivo na tabela mais de uma vez: {arquivo}")

    for arquivo in universo:
        for linha in por_arquivo.get(arquivo, []):
            real = contar_linhas(raiz / arquivo)
            if linha.total != real:
                erros.append(
                    f"{arquivo}: a tabela diz {linha.lidas}/{linha.total} linhas, mas o arquivo tem {real}"
                )
            if linha.lidas < linha.total and linha.resultado != "NÃO CONFERIDO":
                erros.append(
                    f"{arquivo}: {linha.lidas}/{linha.total} linhas lidas com resultado "
                    f"{linha.resultado} — leitura parcial só vale como NÃO CONFERIDO"
                )
            if linha.resultado == "CERTIFICADO" and _normalizar(linha.evidencia) in _VAZIO:
                erros.append(f"{arquivo}: CERTIFICADO sem evidência")
            if linha.resultado in ("CORTA", "NÃO ANALÍTICO") and not linha.pontos:
                erros.append(f"{arquivo}: {linha.resultado} sem ponto citado na coluna Ponto")
            for identificador in linha.pontos:
                if identificador not in pontos:
                    erros.append(f"{arquivo}: cita o ponto {identificador}, que não existe no relatório")

    for identificador in sorted(pontos):
        erros.extend(_conferir_ponto(pontos[identificador], texto_excecoes))

    ocorrencias = varrer(raiz, universo)
    erros.extend(_conferir_citacoes(ocorrencias, texto_relatorio))

    contagem = {resultado: 0 for resultado in RESULTADOS}
    for arquivo in universo:
        for linha in por_arquivo.get(arquivo, []):
            contagem[linha.resultado] = contagem.get(linha.resultado, 0) + 1
    aguardando = sum(
        1
        for ponto in pontos.values()
        if (_campo(ponto, "Classe") or "").strip().upper() != "NA"
        and _normalizar(_campo(ponto, "Estado") or "") == _normalizar(ESTADO_ABERTO)
    )

    saida.append(
        f"{len(universo)} arquivos, {contagem['CERTIFICADO']} certificados, {contagem['CORTA']} cortam, "
        f"{contagem['NÃO ANALÍTICO']} não analíticos, {contagem['NÃO CONFERIDO']} não conferidos, "
        f"{aguardando} ponto(s) aguardando decisão de Sidarta"
    )
    saida.append(f"{len(ocorrencias)} ocorrência(s) da varredura mecânica, todas com destino no relatório")

    if erros:
        saida.append("")
        saida.append(f"{len(erros)} inconsistência(s):")
        saida.extend(f"  - {erro}" for erro in erros)
        return 1, saida
    if contagem["NÃO CONFERIDO"]:
        saida.append("")
        saida.append(
            f"aviso: {contagem['NÃO CONFERIDO']} arquivo(s) NÃO CONFERIDO — coerente, mas incompleto"
        )
        return 2, saida
    return 0, saida


def _relatorio_padrao(raiz: Path) -> Path | None:
    candidatos = sorted((raiz / "docs" / "docs").glob("doc_079_*.md"))
    return candidatos[-1] if candidatos else None


def main(argv: list[str] | None = None) -> int:
    analisador = argparse.ArgumentParser(description="Confere o relatório de auditoria do brief 079.")
    analisador.add_argument("--raiz", default=".", help="raiz do repositório (padrão: pasta atual)")
    analisador.add_argument("--relatorio", default=None, help="caminho do relatório doc_079_*.md")
    analisador.add_argument("--excecoes", default=None, help="caminho do registro de exceções")
    analisador.add_argument(
        "--varredura", action="store_true", help="só imprime as ocorrências da varredura mecânica"
    )
    argumentos = analisador.parse_args(argv)

    raiz = Path(argumentos.raiz).resolve()
    if argumentos.varredura:
        for ocorrencia in varrer(raiz, enumerar_universo(raiz)):
            print(f"{ocorrencia.arquivo}:{ocorrencia.linha}\t{ocorrencia.rotulo}\t{ocorrencia.codigo}")
        return 0

    relatorio = Path(argumentos.relatorio) if argumentos.relatorio else _relatorio_padrao(raiz)
    if relatorio is None or not relatorio.exists():
        print("relatório doc_079_*.md não encontrado em docs/docs/")
        return 1
    excecoes = (
        Path(argumentos.excecoes) if argumentos.excecoes else raiz / "docs" / "EXCECOES_TEXTO_INTEGRAL.md"
    )

    codigo, saida = verificar(raiz, relatorio, excecoes)
    print("\n".join(saida))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
