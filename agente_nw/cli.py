from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

import httpx
import yaml
from pydantic import ValidationError

from agente_nw.coleta.rss import leitor
from agente_nw.console.app import criar_app
from agente_nw.nucleo.agrupamento import agrupador
from agente_nw.nucleo.agrupamento import calibracao as calibracao_agrupamento
from agente_nw.nucleo.agrupamento.agrupador import ClienteEmbeddagem
from agente_nw.nucleo.database import backup, conexao
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, perfil_tema, perfis, sistema
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.modelos.configuracao import TemasArquivo
from agente_nw.nucleo.relevancia import cartoes, cruzamento, qualificador
from agente_nw.nucleo.saidas import markdown
from agente_nw.perfil import agenda_google_csv, agenda_macos, extrator
from agente_nw.perfil.importador import importar as importar_contatos
from agente_nw.perfil.lacunas import ORDEM_IMPACTO, campos_faltando
from agente_nw.perfil.normalizacao import telefone_e164
from config.container import (
    RAIZ,
    banco,
    caminho_banco,
    caminho_limiares_yaml,
    caminho_log_chamadas_llm,
    caminho_pasta_adr,
    caminho_pasta_backups,
    caminho_pasta_saida,
    caminho_sentinela,
    configuracao,
    http,
    llm,
)

MODELOS_OBRIGATORIOS: list[str] = ["qwen3:4b", "bge-m3", "qwen3:8b"]

COMANDOS_RESERVADOS: dict[str, int] = {
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
        "Ollama.app está rodando — feche o aplicativo e suba 'ollama serve' manualmente num terminal"
        if app_rodando
        else "ok"
    )
    return ItemVerificacao(nome, not app_rodando, detalhe, obrigatorio=False)


def _verificar_arquivo_existe(nome: str, caminho: Path) -> ItemVerificacao:
    existe = caminho.exists()
    detalhe = str(caminho) if existe else f"{caminho} não existe"
    return ItemVerificacao(nome, existe, detalhe, obrigatorio=False)


def _verificar_playwright_chromium() -> ItemVerificacao:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as erro:
        return ItemVerificacao(
            "Playwright + Chromium instalados",
            False,
            f"lib Playwright ausente: {erro} — rode 'pip install -e .[dev]'",
            obrigatorio=True,
        )
    try:
        with sync_playwright() as p:
            caminho = Path(p.chromium.executable_path)
    except Exception as erro:
        return ItemVerificacao(
            "Playwright + Chromium instalados",
            False,
            f"erro ao consultar Chromium: {erro} — rode 'playwright install chromium'",
            obrigatorio=True,
        )
    if not caminho.exists():
        return ItemVerificacao(
            "Playwright + Chromium instalados",
            False,
            f"{caminho} não existe — rode 'playwright install chromium'",
            obrigatorio=True,
        )
    return ItemVerificacao("Playwright + Chromium instalados", True, str(caminho), obrigatorio=True)


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
        _verificar_playwright_chromium(),
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


def importar_temas(
    arquivo: str,
    simular: bool,
    conexao_bd: sqlite3.Connection | None = None,
    cliente_llm: ClienteEmbeddagem | None = None,
) -> int:
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

    from agente_nw.perfil.configurador import salvar_perfil_usuario

    conn = conexao_bd if conexao_bd is not None else banco()
    cliente = cliente_llm if cliente_llm is not None else llm()
    agora = datetime.now(UTC).isoformat()

    usuario = salvar_perfil_usuario(
        conn, cliente, temas_arquivo.usuario.nome, temas_arquivo.usuario.temas, agora
    )

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


def agrupar_cmd() -> int:
    cfg = configuracao()
    data_referencia = datetime.now(UTC).isoformat()
    resumo = agrupador.agrupar(llm(), banco(), cfg.limiares, caminho_sentinela(), data_referencia)

    print(f"Itens embeddados: {resumo.itens_embeddados}")
    print(f"Assuntos criados: {resumo.assuntos_criados}")
    print(f"Itens vinculados: {resumo.itens_vinculados}")
    print(f"Republicações: {resumo.republicacoes}")
    print(f"Assuntos reabertos: {resumo.assuntos_reabertos}")
    print(f"Assuntos encerrados: {resumo.assuntos_encerrados}")
    print(f"Assuntos divididos: {resumo.assuntos_divididos}")
    return 0


def calibrar_agrupamento_cmd() -> int:
    caminho_adr = caminho_pasta_adr() / "adr-0001-limiar-agrupamento.md"
    resumo = calibracao_agrupamento.calibrar(llm(), banco(), caminho_limiares_yaml(), caminho_adr)

    print(f"Pares na banda de dúvida amostrados: {resumo.pares_na_banda}")
    print(f"Pares de controle amostrados: {resumo.pares_controle}")
    print(f"Pares avaliados pelo qwen3:8b: {resumo.pares_avaliados}")
    print(f"Limiar anterior: {resumo.limiar_anterior}")
    print(f"Limiar novo: {resumo.limiar_novo}")
    print(f"ADR escrito em: {resumo.caminho_adr}")
    return 0


def qualificar_cmd(limite: int | None) -> int:
    cfg = configuracao()
    limite_efetivo = limite if limite is not None else cfg.limiares.qualificacao.teto_por_dia
    resumo = qualificador.qualificar_pendentes(llm(), banco(), limite_efetivo)

    print(f"Candidatos: {resumo.candidatos}")
    print(f"Títulos gerados: {resumo.titulos_gerados}")
    print(f"Qualificados: {resumo.qualificados}")
    print(f"Erros: {resumo.erros}")
    return 0


def cartao_cmd(assunto_id: int) -> int:
    try:
        resultado = cartoes.gerar_cartao(llm(), banco(), assunto_id)
    except ValueError as erro:
        print(f"FALHA: {erro}")
        return 1

    if resultado is None:
        print("FALHA: não foi possível gerar um cartão válido (ver fila_revisao)")
        return 1

    print(resultado)
    return 0


def cruzar_cmd() -> int:
    cfg = configuracao()
    conn = banco()
    cliente = llm()
    agora = datetime.now(UTC).isoformat()

    contatos_ativos = perfis.listar_ativos(conn)
    if not contatos_ativos:
        print("Nenhum contato ativo.")
        return 0

    for contato in contatos_ativos:
        assert contato.id is not None
        resumo = cruzamento.cruzar_contato(cliente, conn, contato.id, cfg.limiares, agora)
        if resumo.sem_assunto:
            print(f"{contato.nome}: sem_assunto — {resumo.motivo}")
        else:
            print(
                f"{contato.nome}: {resumo.conectores} conector(es), {resumo.viaveis} viável(is), "
                f"{resumo.descartados} descartado(s), {resumo.erros} erro(s) de por_que"
            )
    return 0


def menu_cmd(telefone: str) -> int:
    telefone_normalizado = telefone_e164(telefone)
    conn = banco()
    perfil = perfis.obter_por_telefone_ou_email(conn, telefone_normalizado, None)
    if perfil is None:
        print(f"FALHA: nenhum contato encontrado com o telefone '{telefone}'")
        return 1
    assert perfil.id is not None

    hoje = datetime.now(UTC).date().isoformat()
    registros = [r for r in assunto_contato.listar_do_dia(conn, perfil.id, hoje) if r.status != "descartado"]
    if not registros:
        print(f"Nenhum assunto no menu de hoje ({hoje}) para {perfil.nome}.")
        return 0

    for registro in registros:
        assunto = assuntos.obter_por_id(conn, registro.assunto_id)
        titulo = assunto.titulo_gerado if assunto is not None else f"assunto #{registro.assunto_id}"
        print(f"[{registro.tipo}] {titulo} (score={registro.score:.1f})")
        if registro.por_que:
            print(f"  por quê: {registro.por_que}")
    return 0


def exportar_menu_cmd(data: str | None) -> int:
    conn = banco()
    data_efetiva = data if data is not None else datetime.now(UTC).date().isoformat()

    perfis_ativos = perfis.listar_ativos(conn)
    texto = markdown.gerar(conn, perfis_ativos, data_efetiva)

    pasta = caminho_pasta_saida()
    pasta.mkdir(parents=True, exist_ok=True)
    caminho_arquivo = pasta / f"menu_{data_efetiva}.md"
    caminho_arquivo.write_text(texto, encoding="utf-8")

    print(f"Arquivo gerado em {caminho_arquivo}")
    return 0


def ler_marcacoes_cmd(data: str | None) -> int:
    data_efetiva = data if data is not None else datetime.now(UTC).date().isoformat()
    caminho_arquivo = caminho_pasta_saida() / f"menu_{data_efetiva}.md"
    if not caminho_arquivo.exists():
        print(f"FALHA: {caminho_arquivo} não existe")
        return 1

    conn = banco()
    texto = caminho_arquivo.read_text(encoding="utf-8")
    marcacoes, avisos = markdown.ler_marcacoes(texto)

    aplicadas = 0
    for marcacao_lida in marcacoes:
        if marcacao_lida.resultado == "usado":
            sucesso = assunto_contato.marcar_usado(conn, marcacao_lida.ac_id)
        else:
            assert marcacao_lida.motivo is not None
            sucesso = assunto_contato.marcar_nao_serve(conn, marcacao_lida.ac_id, marcacao_lida.motivo)

        if sucesso:
            aplicadas += 1
        else:
            avisos.append(f"ac:{marcacao_lida.ac_id} não encontrado ou já resolvido")
    conn.commit()

    print(f"Marcações aplicadas: {aplicadas}")
    if avisos:
        print(f"Avisos ({len(avisos)}):")
        for aviso in avisos:
            print(f"  - {aviso}")
    return 0


def _lista_de_csv(bruto: str) -> list[str]:
    return [pedaco.strip() for pedaco in bruto.split(",") if pedaco.strip()]


def preparar_cmd(
    telefone: str, assunto: str, meio: str, objetivo: str, interessa: str, evitar: str, livre: str
) -> int:
    telefone_normalizado = telefone_e164(telefone)
    conn = banco()
    perfil = perfis.obter_por_telefone_ou_email(conn, telefone_normalizado, None)
    if perfil is None:
        print(f"FALHA: nenhum contato encontrado com o telefone '{telefone}'")
        return 1
    assert perfil.id is not None

    from agente_nw.coleta.capturas.playwright_backend import abrir_pagina_playwright
    from agente_nw.nucleo.consulta import preparar
    from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta, MeioContato

    if meio not in ("pessoalmente", "telefone", "whatsapp", "carta", "outro"):
        print(f"FALHA: meio inválido '{meio}'")
        return 1

    contexto = ContextoConsulta(
        assunto=assunto,
        meio=meio,  # type: ignore[arg-type]
        objetivo=objetivo,
        interessa=_lista_de_csv(interessa),
        evitar=_lista_de_csv(evitar),
        livre=livre,
    )
    _ = MeioContato  # mantém o import usado pelo type: ignore acima

    cfg = configuracao()
    agora = datetime.now(UTC).isoformat()
    resultado = preparar(
        conexao=conn,
        cliente_llm=llm(),
        cliente_http=http(),
        perfil_id=perfil.id,
        contexto=contexto,
        limiares=cfg.limiares,
        caminho_fontes=RAIZ / "fontes.yaml",
        caminho_sentinela=caminho_sentinela(),
        abrir_pagina=abrir_pagina_playwright,
        pasta_navegador=RAIZ / "dados" / "navegador",
        agora=agora,
    )

    print(f"Consulta #{resultado.consulta_id} gravada para {perfil.nome}.")
    resumo_rede = resultado.resumo_rede_social
    print(
        f"Rede social — redes lidas: {resumo_rede.redes_lidas}, "
        f"blocos: {resumo_rede.blocos_capturados}, fatos: {resumo_rede.fatos_gravados}, "
        f"sem sessão: {resumo_rede.redes_sem_sessao}"
    )
    for motivo in resumo_rede.motivos_sem_sessao:
        print(f"  - {motivo}")

    if resultado.aviso:
        print(f"AVISO: {resultado.aviso}")

    for item in resultado.itens_menu:
        print(f"[{item.tipo}] {item.titulo} (score={item.score:.1f})")
        if item.por_que:
            print(f"  por quê: {item.por_que}")

    if resultado.historico_texto:
        print("--- Histórico recente ---")
        print(resultado.historico_texto)

    return 0


def ler_rede_social_cmd(telefone: str) -> int:
    telefone_normalizado = telefone_e164(telefone)
    conn = banco()
    perfil = perfis.obter_por_telefone_ou_email(conn, telefone_normalizado, None)
    if perfil is None:
        print(f"FALHA: nenhum contato encontrado com o telefone '{telefone}'")
        return 1
    assert perfil.id is not None

    from agente_nw.coleta.capturas.leitor import ler_redes_sociais_do_contato
    from agente_nw.coleta.capturas.playwright_backend import abrir_pagina_playwright

    agora = datetime.now(UTC).isoformat()
    pasta_navegador = RAIZ / "dados" / "navegador"
    resumo = ler_redes_sociais_do_contato(
        llm(), conn, perfil.id, abrir_pagina_playwright, pasta_navegador, agora
    )

    print(f"Redes lidas: {resumo.redes_lidas}")
    print(f"Redes sem sessão: {resumo.redes_sem_sessao}")
    print(f"Blocos capturados: {resumo.blocos_capturados}")
    print(f"Fatos gravados: {resumo.fatos_gravados}")
    for motivo in resumo.motivos_sem_sessao:
        print(f"  - {motivo}")
    return 0


def _dias_no_intervalo(desde: str, ate: str) -> list[str]:
    inicio = date.fromisoformat(desde)
    fim = date.fromisoformat(ate)
    dias: list[str] = []
    atual = inicio
    while atual <= fim:
        dias.append(atual.isoformat())
        atual += timedelta(days=1)
    return dias


def _ler_chamadas_llm(desde: str, ate: str) -> list[dict[str, object]]:
    caminho = caminho_log_chamadas_llm()
    if not caminho.exists():
        return []

    resultado: list[dict[str, object]] = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        registro = json.loads(linha)
        dia = str(registro.get("quando", ""))[:10]
        if desde <= dia <= ate:
            resultado.append(registro)
    return resultado


def certificar_cmd(desde: str, ate: str) -> int:
    conn = banco()
    dias = _dias_no_intervalo(desde, ate)

    total_usado_geral = 0
    total_entregue_geral = 0

    for dia in dias:
        print(f"=== {dia} ===")
        contagens_status = assunto_contato.contar_por_status(conn, dia)
        contagens_tipo = assunto_contato.contar_por_perfil_e_tipo(conn, dia)
        perfis_com_sugestao = {perfil_id for perfil_id, _tipo, _quantidade in contagens_tipo}
        total_entregue = sum(
            quantidade for status, quantidade in contagens_status.items() if status != "descartado"
        )
        usados = contagens_status.get("usado", 0)
        total_usado_geral += usados
        total_entregue_geral += total_entregue

        print(f"  Contatos com sugestão: {len(perfis_com_sugestao)}")
        print(
            f"  Assuntos entregues: {total_entregue} (usado: {usados}, "
            f"não serve: {contagens_status.get('nao_serve', 0)}, "
            f"novo/pendente: {contagens_status.get('novo', 0)})"
        )
        for perfil_id, tipo, quantidade in sorted(contagens_tipo):
            print(f"    perfil {perfil_id} [{tipo}]: {quantidade}")

    print("=== Resumo agregado ===")
    if total_entregue_geral:
        print(
            f"Aproveitamento geral: {total_usado_geral}/{total_entregue_geral} "
            f"({total_usado_geral / total_entregue_geral:.1%})"
        )
    else:
        print("Aproveitamento geral: sem assuntos entregues no período.")

    chamadas = _ler_chamadas_llm(desde, ate)
    if chamadas:
        sucesso_primeira = sum(
            1 for c in chamadas if c.get("tentativas_usadas") == 1 and c.get("sucesso") is True
        )
        print(f"Chamadas de LLM no período: {len(chamadas)}")
        print(
            f"Sucesso na primeira tentativa: {sucesso_primeira}/{len(chamadas)} "
            f"({sucesso_primeira / len(chamadas):.1%})"
        )
    else:
        print("Nenhuma chamada de LLM registrada no período.")

    orfaos = assunto_contato.contar_orfaos(conn)
    print(f"assunto_contato órfãos (deveria ser sempre 0): {orfaos}")

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


def console_cmd(caminho_banco_str: str, porta: int) -> int:
    caminho_banco_console = Path(caminho_banco_str)
    if not caminho_banco_console.exists():
        print(f"FALHA: {caminho_banco_console} não existe")
        return 1

    cfg = configuracao()
    caminho_log_llm = RAIZ / "dados" / "logs" / "console_chamadas_llm.jsonl"
    app = criar_app(
        caminho_banco_console, caminho_log_llm, cfg.roteamento, cfg.limiares, cfg.local.ollama_url
    )
    app.run(host="127.0.0.1", port=porta)
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
    subparsers.add_parser("agrupar")
    subparsers.add_parser("calibrar-agrupamento")

    certificar_parser = subparsers.add_parser("certificar")
    certificar_parser.add_argument("--desde", required=True)
    certificar_parser.add_argument("--ate", required=True)

    qualificar_parser = subparsers.add_parser("qualificar")
    qualificar_parser.add_argument("--limite", type=int, default=None)

    cartao_parser = subparsers.add_parser("cartao")
    cartao_parser.add_argument("assunto_id", type=int)

    subparsers.add_parser("cruzar")

    menu_parser = subparsers.add_parser("menu")
    menu_parser.add_argument("telefone")

    exportar_menu_parser = subparsers.add_parser("exportar-menu")
    exportar_menu_parser.add_argument("--data", default=None)

    ler_marcacoes_parser = subparsers.add_parser("ler-marcacoes")
    ler_marcacoes_parser.add_argument("--data", default=None)

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

    console_parser = subparsers.add_parser("console")
    console_parser.add_argument("--banco", required=True)
    console_parser.add_argument("--porta", type=int, default=8765)

    ler_rede_social_parser = subparsers.add_parser("ler-rede-social")
    ler_rede_social_parser.add_argument("telefone")

    preparar_parser = subparsers.add_parser("preparar")
    preparar_parser.add_argument("--telefone", required=True)
    preparar_parser.add_argument("--assunto", required=True)
    preparar_parser.add_argument(
        "--meio", required=True, choices=["pessoalmente", "telefone", "whatsapp", "carta", "outro"]
    )
    preparar_parser.add_argument("--objetivo", required=True)
    preparar_parser.add_argument("--interessa", default="")
    preparar_parser.add_argument("--evitar", default="")
    preparar_parser.add_argument("--livre", default="")

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
    if args.comando == "agrupar":
        return agrupar_cmd()
    if args.comando == "calibrar-agrupamento":
        return calibrar_agrupamento_cmd()
    if args.comando == "certificar":
        return certificar_cmd(args.desde, args.ate)
    if args.comando == "qualificar":
        return qualificar_cmd(args.limite)
    if args.comando == "cartao":
        return cartao_cmd(args.assunto_id)
    if args.comando == "cruzar":
        return cruzar_cmd()
    if args.comando == "menu":
        return menu_cmd(args.telefone)
    if args.comando == "exportar-menu":
        return exportar_menu_cmd(args.data)
    if args.comando == "ler-marcacoes":
        return ler_marcacoes_cmd(args.data)
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
    if args.comando == "console":
        return console_cmd(args.banco, args.porta)
    if args.comando == "ler-rede-social":
        return ler_rede_social_cmd(args.telefone)
    if args.comando == "preparar":
        return preparar_cmd(
            args.telefone,
            args.assunto,
            args.meio,
            args.objetivo,
            args.interessa,
            args.evitar,
            args.livre,
        )
    if args.comando in COMANDOS_RESERVADOS:
        return _comando_reservado(args.comando, COMANDOS_RESERVADOS[args.comando])

    parser.error(f"comando desconhecido: {args.comando}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
