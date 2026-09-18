from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import httpx
import yaml
from pydantic import ValidationError

from agente_nw.coleta.rss import leitor
from agente_nw.nucleo.database import backup, conexao
from agente_nw.nucleo.database.queries import perfil_tema, perfis, sistema
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.modelos.configuracao import TemasArquivo
from agente_nw.perfil import agenda_google_csv, agenda_macos, extrator
from agente_nw.perfil.importador import importar as importar_contatos
from agente_nw.perfil.lacunas import ORDEM_IMPACTO, campos_faltando
from agente_nw.perfil.normalizacao import telefone_e164
from config.container import (
    RAIZ,
    banco,
    caminho_banco,
    caminho_pasta_backups,
    caminho_sentinela,
    configuracao,
    http,
    llm,
)

MODELOS_OBRIGATORIOS: list[str] = ["qwen3:4b", "bge-m3", "qwen3:8b"]

COMANDOS_RESERVADOS: dict[str, int] = {
    "ciclo": 12,
    "exportar-menu": 11,
    "ler-marcacoes": 11,
    "calibrar-agrupamento": 7,
    "calibrar-conector": 9,
}


class ItemVerificacao(NamedTuple):
    nome: str
    ok: bool
    detalhe: str
    obrigatorio: bool


def _verificar_python() -> ItemVerificacao:
    versao = sys.version_info
    ok = versao.major == 3 and versao.minor == 12
    detalhe = f"{versao.major}.{versao.minor}.{versao.micro}"
    return ItemVerificacao("Python 3.12.x", ok, detalhe, obrigatorio=True)


def _verificar_sqlite_vec() -> ItemVerificacao:
    try:
        conexao_memoria = conexao.abrir(":memory:")
        versao_vec = sistema.vec_version(conexao_memoria)
        conexao_memoria.close()
        return ItemVerificacao(
            "sqlite-vec carrega em conexão em memória",
            True,
            f"vec_version={versao_vec}, sqlite3={sqlite3.sqlite_version}",
            obrigatorio=True,
        )
    except Exception as erro:
        return ItemVerificacao(
            "sqlite-vec carrega em conexão em memória",
            False,
            f"{erro} — verifique 'brew install python@3.12' e recrie o venv",
            obrigatorio=True,
        )


def _buscar_tags_ollama(cliente: httpx.Client, ollama_url: str) -> list[str] | None:
    try:
        resposta = cliente.get(f"{ollama_url}/api/tags", timeout=5.0)
        resposta.raise_for_status()
        modelos: list[dict[str, str]] = resposta.json().get("models", [])
        return [modelo["name"] for modelo in modelos]
    except Exception:
        return None


def _verificar_ollama(cliente: httpx.Client, ollama_url: str) -> ItemVerificacao:
    nomes = _buscar_tags_ollama(cliente, ollama_url)
    return ItemVerificacao("Ollama responde", nomes is not None, ollama_url, obrigatorio=True)


def _verificar_modelos(cliente: httpx.Client, ollama_url: str) -> list[ItemVerificacao]:
    nomes_instalados = _buscar_tags_ollama(cliente, ollama_url)
    if nomes_instalados is None:
        detalhe = "não verificado — Ollama não respondeu"
        return [
            ItemVerificacao(f"Modelo {modelo}", False, detalhe, obrigatorio=True)
            for modelo in MODELOS_OBRIGATORIOS
        ]

    itens: list[ItemVerificacao] = []
    for modelo in MODELOS_OBRIGATORIOS:
        presente = any(
            instalado == modelo or instalado.startswith(f"{modelo}:") for instalado in nomes_instalados
        )
        detalhe = "presente" if presente else f"ausente — ollama pull {modelo}"
        itens.append(ItemVerificacao(f"Modelo {modelo}", presente, detalhe, obrigatorio=True))
    return itens


def _verificar_ollama_app_na_porta() -> ItemVerificacao:
    nome = "Servidor não é o Ollama.app"
    try:
        saida = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5).stdout
    except Exception as erro:
        return ItemVerificacao(nome, True, f"não verificado: {erro}", obrigatorio=False)

    app_rodando = "Ollama.app" in saida
    detalhe = (
        "Ollama.app está rodando — feche o aplicativo e suba 'ollama serve' pelo LaunchAgent do projeto"
        if app_rodando
        else "ok"
    )
    return ItemVerificacao(nome, not app_rodando, detalhe, obrigatorio=False)


def _verificar_arquivo_existe(nome: str, caminho: Path) -> ItemVerificacao:
    existe = caminho.exists()
    detalhe = str(caminho) if existe else f"{caminho} não existe"
    return ItemVerificacao(nome, existe, detalhe, obrigatorio=False)


def verificar_ambiente() -> int:
    try:
        config = configuracao()
        ollama_url = config.local.ollama_url
    except Exception as erro:
        print(f"FALHA ao carregar configuração: {erro}")
        return 1

    cliente = http()
    itens = [
        _verificar_python(),
        _verificar_sqlite_vec(),
        _verificar_ollama(cliente, ollama_url),
        *_verificar_modelos(cliente, ollama_url),
        _verificar_ollama_app_na_porta(),
        _verificar_arquivo_existe("temas.yaml existe", RAIZ / "temas.yaml"),
        _verificar_arquivo_existe("fontes.yaml existe", RAIZ / "fontes.yaml"),
    ]

    largura = max(len(item.nome) for item in itens)
    houve_falha_obrigatoria = False
    for item in itens:
        rotulo = "OK" if item.ok else ("AVISO" if not item.obrigatorio else "FALHA")
        print(f"{item.nome:<{largura}}  {rotulo:<6}  {item.detalhe}")
        if not item.ok and item.obrigatorio:
            houve_falha_obrigatoria = True

    return 1 if houve_falha_obrigatoria else 0


def importar_temas(arquivo: str, simular: bool, conexao_bd: sqlite3.Connection | None = None) -> int:
    caminho = Path(arquivo)
    if not caminho.exists():
        print(f"FALHA: {caminho} não existe")
        return 1

    try:
        dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
        temas_arquivo = TemasArquivo.model_validate(dados)
    except ValidationError as erro:
        print(f"FALHA de validação em {caminho}:\n{erro}")
        return 1

    if simular:
        print(f"Usuário: {temas_arquivo.usuario.nome}")
        print(f"{len(temas_arquivo.usuario.temas)} tema(s) seriam importados:")
        for tema in temas_arquivo.usuario.temas:
            sinonimos = ", ".join(tema.sinonimos) if tema.sinonimos else "—"
            print(f"  - {tema.nome}  [nível={tema.nivel}, peso={tema.peso}, sinônimos={sinonimos}]")
        if temas_arquivo.ignorar:
            print(f"Termos a ignorar: {', '.join(temas_arquivo.ignorar)}")
        return 0

    conn = conexao_bd if conexao_bd is not None else banco()
    agora = datetime.now(UTC).isoformat()

    usuario = perfis.upsert_usuario(conn, temas_arquivo.usuario.nome, agora)
    assert usuario.id is not None
    for tema in temas_arquivo.usuario.temas:
        tema_gravado = queries_temas.obter_ou_criar(conn, tema.nome, tema.descricao, tema.sinonimos, agora)
        assert tema_gravado.id is not None
        perfil_tema.vincular(
            conn,
            usuario.id,
            tema_gravado.id,
            tema.peso,
            "declarada",
            tema.nivel,
            True,
            agora,
        )
    conn.commit()

    print(f"Usuário: {usuario.nome}")
    print(f"{len(temas_arquivo.usuario.temas)} tema(s) gravados no banco.")
    return 0


def coletar() -> int:
    caminho_fontes = RAIZ / "fontes.yaml"
    if not caminho_fontes.exists():
        print(f"FALHA: {caminho_fontes} não existe")
        return 1

    cfg = configuracao()
    resumo = leitor.coletar(banco(), http(), caminho_fontes, cfg.limiares.coleta, caminho_sentinela())

    print(f"Fontes processadas: {resumo.fontes_processadas}")
    print(f"Itens novos: {resumo.itens_novos}")
    print(f"Duplicados: {resumo.duplicados}")
    print(f"Descartados por ruído: {resumo.descartados_ruido}")
    if resumo.alertas_feed_vazio:
        nomes = ", ".join(resumo.alertas_feed_vazio)
        print(f"ALERTA — sem novidade em duas execuções seguidas: {nomes}")
    print(f"Tempo total: {resumo.tempo_segundos:.1f}s")
    return 0


def migrar() -> int:
    conn = banco()
    print(f"Esquema na versão {sistema.versao_esquema(conn)}")
    return 0


def fazer_backup_cmd() -> int:
    conn = banco()
    caminho = backup.fazer_backup(conn, caminho_pasta_backups())
    print(f"Backup criado em {caminho}")
    return 0


def copiar_banco(destino: str) -> int:
    destino_path = Path(destino)
    if destino_path.resolve() == caminho_banco().resolve():
        print("FALHA: destino não pode ser o banco real")
        return 1

    mais_recente = backup.backup_mais_recente(caminho_pasta_backups())
    if mais_recente is None:
        print(f"FALHA: nenhum backup encontrado em {caminho_pasta_backups()}")
        return 1

    backup.copiar_para(mais_recente, destino_path)
    print(f"Cópia de desenvolvimento criada em {destino_path}, a partir de {mais_recente}")
    return 0


def restaurar_backup(arquivo: str, confirmo: bool) -> int:
    arquivo_path = Path(arquivo)
    if not arquivo_path.exists():
        print(f"FALHA: {arquivo_path} não existe")
        return 1

    if not confirmo:
        print(
            f"Restauraria {arquivo_path} sobre {caminho_banco()}, depois de fazer backup do atual. "
            "Rode de novo com --confirmo."
        )
        return 0

    conn = banco()
    backup.fazer_backup(conn, caminho_pasta_backups())
    conn.close()
    backup.restaurar(arquivo_path, caminho_banco())
    print(f"Banco restaurado a partir de {arquivo_path}")
    return 0


def processar_fila_cmd() -> int:
    resumo = extrator.processar_fila(llm(), banco())

    print(f"Itens processados: {resumo.itens_processados}")
    print(f"Tags gravadas: {resumo.tags_gravadas}")
    print(f"Campos gravados: {resumo.campos_gravados}")
    print(f"Fatos gravados: {resumo.fatos_gravados}")
    if resumo.descartes_por_categoria:
        for categoria, quantidade in sorted(resumo.descartes_por_categoria.items()):
            print(f"Descartes ({categoria}): {quantidade}")
    else:
        print("Descartes: 0")
    print(f"Erros: {resumo.erros}")
    return 0


def importar_agenda_cmd(fonte: str, arquivo: str | None) -> int:
    if fonte == "macos":
        if not agenda_macos.solicitar_permissao():
            print(
                "FALHA: permissão de acesso à agenda negada. Libere manualmente em "
                "Ajustes do Sistema → Privacidade e Segurança → Contatos."
            )
            return 1
        contatos = agenda_macos.ler_contatos()
    elif fonte == "csv":
        if not arquivo:
            print("FALHA: --arquivo é obrigatório com --fonte csv")
            return 1
        caminho = Path(arquivo)
        if not caminho.exists():
            print(f"FALHA: {caminho} não existe")
            return 1
        contatos = agenda_google_csv.ler_contatos(caminho)
    else:
        print(f"FALHA: fonte desconhecida '{fonte}' — use 'macos' ou 'csv'")
        return 1

    resumo = importar_contatos(contatos, banco())
    print(f"Contatos lidos: {resumo.contatos_lidos}")
    print(f"Contatos ignorados (sem nome nem telefone/e-mail): {resumo.contatos_ignorados}")
    print(f"Perfis criados: {resumo.perfis_criados}")
    print(f"Perfis atualizados: {resumo.perfis_atualizados}")
    print(f"Tags vinculadas: {resumo.tags_vinculadas}")
    print(f"Notas enfileiradas para extração: {resumo.notas_enfileiradas}")
    return 0


def ficha_cmd(telefone: str) -> int:
    telefone_normalizado = telefone_e164(telefone)
    conn = banco()
    perfil = perfis.obter_por_telefone_ou_email(conn, telefone_normalizado, None)
    if perfil is None:
        print(f"FALHA: nenhum contato encontrado com o telefone '{telefone}'")
        return 1
    assert perfil.id is not None

    print(f"Nome: {perfil.nome}")
    lacunas = set(campos_faltando(perfil))
    for campo in ORDEM_IMPACTO:
        valor = getattr(perfil, campo)
        print(f"  {campo}: (vazio)" if campo in lacunas else f"  {campo}: {valor}")
    print(f"Ativo: {'sim' if perfil.ativo else 'não'}")
    print(f"Gerar agora: {'sim' if perfil.gerar_agora else 'não'}")

    tags = perfil_tema.listar_por_perfil(conn, perfil.id)
    confirmadas = [tag for tag in tags if tag.confirmado]
    nao_confirmadas = [tag for tag in tags if not tag.confirmado]

    if confirmadas:
        print("Tags confirmadas:")
        for tag in confirmadas:
            tema = queries_temas.obter_por_id(conn, tag.tema_id)
            nome_tema = tema.nome if tema is not None else f"tema #{tag.tema_id}"
            print(f"  - {nome_tema}")

    if nao_confirmadas:
        print("Tags não confirmadas:")
        for indice, tag in enumerate(nao_confirmadas, start=1):
            tema = queries_temas.obter_por_id(conn, tag.tema_id)
            nome_tema = tema.nome if tema is not None else f"tema #{tag.tema_id}"
            print(f"  {indice}. {nome_tema}")

    return 0


def ativar_cmd(telefone: str) -> int:
    telefone_normalizado = telefone_e164(telefone)
    conn = banco()
    perfil = perfis.obter_por_telefone_ou_email(conn, telefone_normalizado, None)
    if perfil is None:
        print(f"FALHA: nenhum contato encontrado com o telefone '{telefone}'")
        return 1
    assert perfil.id is not None

    perfis.ativar(conn, perfil.id)
    conn.commit()
    print(f"{perfil.nome} ativado.")
    return 0


def confirmar_tags_cmd(telefone: str, todas: bool, ids: str | None) -> int:
    telefone_normalizado = telefone_e164(telefone)
    conn = banco()
    perfil = perfis.obter_por_telefone_ou_email(conn, telefone_normalizado, None)
    if perfil is None:
        print(f"FALHA: nenhum contato encontrado com o telefone '{telefone}'")
        return 1
    assert perfil.id is not None

    tags = perfil_tema.listar_por_perfil(conn, perfil.id)
    nao_confirmadas = [tag for tag in tags if not tag.confirmado]
    if not nao_confirmadas:
        print("Nenhuma tag pendente de confirmação.")
        return 0

    if todas:
        indices = list(range(1, len(nao_confirmadas) + 1))
    elif ids:
        indices = []
        for pedaco in ids.split(","):
            pedaco = pedaco.strip()
            if pedaco.isdigit():
                indices.append(int(pedaco))
            else:
                print(f"AVISO: índice inválido ignorado: '{pedaco}'")
    else:
        print("FALHA: use --todas ou --ids")
        return 1

    confirmadas = 0
    for indice in indices:
        if indice < 1 or indice > len(nao_confirmadas):
            print(f"AVISO: índice {indice} fora do intervalo (1 a {len(nao_confirmadas)}), ignorado")
            continue
        tag = nao_confirmadas[indice - 1]
        perfil_tema.confirmar(conn, perfil.id, tag.tema_id)
        confirmadas += 1

    conn.commit()
    print(f"{confirmadas} tag(s) confirmada(s).")
    return 0


def _comando_reservado(nome: str, brief: int) -> int:
    print(f"'{nome}' disponível a partir do brief {brief:03d}")
    return 0


def _montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agente_nw")
    subparsers = parser.add_subparsers(dest="comando", required=True)

    subparsers.add_parser("verificar-ambiente")

    importar_temas_parser = subparsers.add_parser("importar-temas")
    importar_temas_parser.add_argument("--arquivo", default="temas.yaml")
    importar_temas_parser.add_argument("--simular", action="store_true")

    subparsers.add_parser("migrar")
    subparsers.add_parser("backup")
    subparsers.add_parser("coletar")
    subparsers.add_parser("processar-fila")

    copiar_banco_parser = subparsers.add_parser("copiar-banco")
    copiar_banco_parser.add_argument("destino")

    restaurar_backup_parser = subparsers.add_parser("restaurar-backup")
    restaurar_backup_parser.add_argument("arquivo")
    restaurar_backup_parser.add_argument("--confirmo", action="store_true")

    importar_agenda_parser = subparsers.add_parser("importar-agenda")
    importar_agenda_parser.add_argument("--fonte", required=True, choices=["macos", "csv"])
    importar_agenda_parser.add_argument("--arquivo")

    ficha_parser = subparsers.add_parser("ficha")
    ficha_parser.add_argument("telefone")

    ativar_parser = subparsers.add_parser("ativar")
    ativar_parser.add_argument("telefone")

    confirmar_tags_parser = subparsers.add_parser("confirmar-tags")
    confirmar_tags_parser.add_argument("telefone")
    grupo_confirmar = confirmar_tags_parser.add_mutually_exclusive_group()
    grupo_confirmar.add_argument("--todas", action="store_true")
    grupo_confirmar.add_argument("--ids")

    for nome in COMANDOS_RESERVADOS:
        subparsers.add_parser(nome)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _montar_parser()
    args = parser.parse_args(argv)

    if args.comando == "verificar-ambiente":
        return verificar_ambiente()
    if args.comando == "importar-temas":
        return importar_temas(args.arquivo, args.simular)
    if args.comando == "migrar":
        return migrar()
    if args.comando == "backup":
        return fazer_backup_cmd()
    if args.comando == "coletar":
        return coletar()
    if args.comando == "processar-fila":
        return processar_fila_cmd()
    if args.comando == "copiar-banco":
        return copiar_banco(args.destino)
    if args.comando == "restaurar-backup":
        return restaurar_backup(args.arquivo, args.confirmo)
    if args.comando == "importar-agenda":
        return importar_agenda_cmd(args.fonte, args.arquivo)
    if args.comando == "ficha":
        return ficha_cmd(args.telefone)
    if args.comando == "ativar":
        return ativar_cmd(args.telefone)
    if args.comando == "confirmar-tags":
        return confirmar_tags_cmd(args.telefone, args.todas, args.ids)
    if args.comando in COMANDOS_RESERVADOS:
        return _comando_reservado(args.comando, COMANDOS_RESERVADOS[args.comando])

    parser.error(f"comando desconhecido: {args.comando}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
