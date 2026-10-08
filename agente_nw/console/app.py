from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import httpx
from flask import Flask, abort, g, redirect, render_template, request, url_for
from pydantic import ValidationError
from werkzeug.wrappers import Response

from agente_nw.coleta.capturas import busca
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import (
    assunto_contato,
    assuntos,
    fila_extracao,
    perfil_tema,
    perfis,
    redes_sociais,
)
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.nucleo.llm import ClienteOllama
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.modelos.configuracao import Limiares, NivelTema, Roteamento, TemaUsuario
from agente_nw.nucleo.modelos.contexto_consulta import ContextoConsulta
from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.modelos.perfil_tema import PerfilTema
from agente_nw.nucleo.modelos.tema import Tema
from agente_nw.nucleo.relevancia import cruzamento
from agente_nw.nucleo.saidas.markdown import _MOTIVOS
from agente_nw.perfil import configurador, extrator
from agente_nw.perfil.lacunas import campos_faltando
from agente_nw.perfil.normalizacao import telefone_e164

_NIVEIS: tuple[NivelTema, ...] = ("dominio", "interesse", "curiosidade")
_MEIOS: tuple[str, ...] = ("pessoalmente", "telefone", "whatsapp", "carta", "outro")


def _lista_de_csv(bruto: str) -> list[str]:
    return [pedaco.strip() for pedaco in bruto.split(",") if pedaco.strip()]


def criar_app(
    caminho_banco: Path,
    caminho_log_llm: Path,
    roteamento: Roteamento,
    limiares: Limiares,
    ollama_url: str,
) -> Flask:
    app = Flask(__name__)

    # Migrações rodam uma vez, aqui, com uma conexão descartada em seguida — cada
    # requisição abre a sua própria conexão (ver _conn), porque o servidor de
    # desenvolvimento do Flask pode atender requisições em uma thread diferente
    # da que criou o app, e sqlite3.Connection não pode atravessar threads.
    conexao_inicial = conexao.abrir(caminho_banco)
    migracoes.aplicar(conexao_inicial)
    conexao_inicial.commit()
    conexao_inicial.close()

    def _conn() -> sqlite3.Connection:
        if "conn" not in g:
            g.conn = conexao.abrir(caminho_banco)
        return cast(sqlite3.Connection, g.conn)

    def _cliente_llm() -> ClienteOllama:
        if "cliente_llm" not in g:
            g.cliente_llm = ClienteOllama(
                httpx.Client(timeout=120.0), _conn(), roteamento, ollama_url, caminho_log_llm
            )
        return cast(ClienteOllama, g.cliente_llm)

    @app.teardown_appcontext
    def _fechar_conexao(exc: BaseException | None) -> None:
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()

    def _perfil_ou_404(perfil_id: int) -> Perfil:
        perfil = perfis.obter_por_id(_conn(), perfil_id)
        if perfil is None:
            abort(404)
        return perfil

    def _usuario_ou_none() -> Perfil | None:
        return perfis.obter_usuario(_conn())

    def _sem_usuario(erro: str | None = None) -> str:
        return render_template("sem_usuario.html", quantidade_slots=5, erro=erro)

    def _com_assunto(itens: list[AssuntoContato]) -> list[tuple[AssuntoContato, Assunto | None]]:
        conn = _conn()
        return [(registro, assuntos.obter_por_id(conn, registro.assunto_id)) for registro in itens]

    @app.route("/")
    def indice() -> Response:
        return redirect(url_for("contatos"))

    @app.route("/contatos")
    def contatos() -> str:
        linhas = [(perfil, len(campos_faltando(perfil))) for perfil in perfis.listar_todos(_conn())]
        return render_template("contatos.html", linhas=linhas)

    @app.route("/contatos/novo", methods=["POST"])
    def novo_contato() -> Response:
        conn = _conn()
        nome = request.form.get("nome", "").strip()
        if not nome:
            abort(400)
        telefone = telefone_e164(request.form.get("telefone", ""))
        email_bruto = request.form.get("email", "").strip()
        email = email_bruto or None
        agora = datetime.now(UTC).isoformat()
        perfil = perfis.inserir_novo_contato(conn, nome, telefone, email, agora)
        conn.commit()
        assert perfil.id is not None
        return redirect(url_for("ficha", perfil_id=perfil.id))

    def _renderizar_ficha(
        perfil_id: int,
        rede_busca: str | None = None,
        resultado_busca: object | None = None,
    ) -> str:
        conn = _conn()
        perfil = _perfil_ou_404(perfil_id)
        tags = perfil_tema.listar_por_perfil(conn, perfil_id)
        tags_com_tema = [(tag, queries_temas.obter_por_id(conn, tag.tema_id)) for tag in tags]
        confirmadas = [(tag, tema) for tag, tema in tags_com_tema if tag.confirmado]
        nao_confirmadas = [(tag, tema) for tag, tema in tags_com_tema if not tag.confirmado]
        redes = redes_sociais.listar_por_perfil(conn, perfil_id)
        outros_contatos = [p for p in perfis.listar_todos(conn) if p.id != perfil_id]
        return render_template(
            "ficha.html",
            perfil=perfil,
            confirmadas=confirmadas,
            nao_confirmadas=nao_confirmadas,
            redes=redes,
            redes_buscaveis=busca.REDES_SUPORTADAS,
            rede_busca=rede_busca,
            resultado_busca=resultado_busca,
            outros_contatos=outros_contatos,
        )

    @app.route("/contatos/<int:perfil_id>")
    def ficha(perfil_id: int) -> str:
        return _renderizar_ficha(perfil_id)

    @app.route("/contatos/<int:perfil_id>/confirmar-tags", methods=["POST"])
    def confirmar_tags(perfil_id: int) -> Response:
        conn = _conn()
        _perfil_ou_404(perfil_id)
        for tema_id_texto in request.form.getlist("tema_id"):
            perfil_tema.confirmar(conn, perfil_id, int(tema_id_texto))
        conn.commit()
        return redirect(url_for("ficha", perfil_id=perfil_id))

    @app.route("/contatos/<int:perfil_id>/ativar", methods=["POST"])
    def ativar(perfil_id: int) -> Response:
        conn = _conn()
        _perfil_ou_404(perfil_id)
        perfis.ativar(conn, perfil_id)
        conn.commit()
        return redirect(url_for("ficha", perfil_id=perfil_id))

    @app.route("/contatos/<int:perfil_id>/editar", methods=["POST"])
    def editar_ficha(perfil_id: int) -> Response:
        conn = _conn()
        _perfil_ou_404(perfil_id)
        nome = request.form.get("nome", "").strip()
        if not nome:
            abort(400)

        def _texto_ou_none(chave: str) -> str | None:
            bruto = request.form.get(chave, "").strip()
            return bruto or None

        tem_filhos_bruto = request.form.get("tem_filhos", "").strip()
        if tem_filhos_bruto == "sim":
            tem_filhos: bool | None = True
        elif tem_filhos_bruto == "nao":
            tem_filhos = False
        else:
            tem_filhos = None

        campos: dict[str, object] = {
            "nome": nome,
            "apelido": _texto_ou_none("apelido"),
            "email": _texto_ou_none("email"),
            "telefone": telefone_e164(request.form.get("telefone", "")),
            "empresa": _texto_ou_none("empresa"),
            "cargo": _texto_ou_none("cargo"),
            "setor": _texto_ou_none("setor"),
            "cidade": _texto_ou_none("cidade"),
            "naturalidade": _texto_ou_none("naturalidade"),
            "linguas": _lista_de_csv(request.form.get("linguas", "")),
            "formacao": _texto_ou_none("formacao"),
            "tem_filhos": tem_filhos,
            "faixa_etaria": _texto_ou_none("faixa_etaria"),
            "notas": _texto_ou_none("notas"),
        }

        agora = datetime.now(UTC).isoformat()
        perfis.atualizar_ficha_manual(conn, perfil_id, campos, agora)
        conn.commit()
        return redirect(url_for("ficha", perfil_id=perfil_id))

    @app.route("/contatos/<int:perfil_id>/apagar", methods=["POST"])
    def apagar_contato(perfil_id: int) -> Response | str:
        conn = _conn()
        perfil = _perfil_ou_404(perfil_id)
        n_fatos, n_consultas = perfis.contagem_historico_protegido(conn, perfil_id)
        bloqueado = n_fatos > 0 or n_consultas > 0
        confirmado = request.form.get("confirmar") == "sim"
        if bloqueado or not confirmado:
            return render_template(
                "confirmar_apagar.html",
                perfil=perfil,
                n_fatos=n_fatos,
                n_consultas=n_consultas,
                bloqueado=bloqueado,
            )
        perfis.apagar_contato_completo(conn, perfil_id)
        conn.commit()
        return redirect(url_for("contatos"))

    @app.route("/contatos/<int:perfil_id>/unir", methods=["POST"])
    def unir_contato(perfil_id: int) -> Response | str:
        conn = _conn()
        canonico = _perfil_ou_404(perfil_id)
        outro_id_bruto = request.form.get("outro_id", "").strip()
        if not outro_id_bruto.isdigit():
            abort(400)
        outro_id = int(outro_id_bruto)
        if outro_id == perfil_id:
            abort(400)
        duplicado = perfis.obter_por_id(conn, outro_id)
        if duplicado is None or duplicado.tipo != "contato":
            abort(400)
        confirmado = request.form.get("confirmar") == "sim"
        if not confirmado:
            n_fatos_dup, n_consultas_dup = perfis.contagem_historico_protegido(conn, outro_id)
            return render_template(
                "confirmar_unir.html",
                canonico=canonico,
                duplicado=duplicado,
                n_fatos_dup=n_fatos_dup,
                n_consultas_dup=n_consultas_dup,
            )
        try:
            perfis.unir_contatos(conn, perfil_id, outro_id)
        except ValueError:
            abort(400)
        conn.commit()
        return redirect(url_for("ficha", perfil_id=perfil_id))

    @app.route("/contatos/<int:perfil_id>/adicionar-texto", methods=["POST"])
    def adicionar_texto(perfil_id: int) -> Response:
        conn = _conn()
        _perfil_ou_404(perfil_id)
        texto = request.form.get("texto", "").strip()
        if texto:
            agora = datetime.now(UTC).isoformat()
            fila_extracao.inserir(conn, perfil_id, texto, "manual", agora)
            conn.commit()
            extrator.processar_fila(_cliente_llm(), conn)
        return redirect(url_for("ficha", perfil_id=perfil_id))

    @app.route("/contatos/<int:perfil_id>/gerar-menu", methods=["POST"])
    def gerar_menu(perfil_id: int) -> Response:
        conn = _conn()
        _perfil_ou_404(perfil_id)
        agora = datetime.now(UTC).isoformat()
        cruzamento.cruzar_contato(_cliente_llm(), conn, perfil_id, limiares, agora)
        return redirect(url_for("menu_contato", perfil_id=perfil_id))

    @app.route("/contatos/<int:perfil_id>/preparar", methods=["GET"])
    def preparar_form(perfil_id: int) -> str:
        perfil = _perfil_ou_404(perfil_id)
        return render_template("preparar.html", perfil=perfil, meios=_MEIOS)

    @app.route("/contatos/<int:perfil_id>/preparar", methods=["POST"])
    def preparar_acao(perfil_id: int) -> Response:
        import httpx

        from agente_nw.coleta.capturas.playwright_backend import abrir_pagina_playwright
        from agente_nw.nucleo import consulta as consulta_mod

        perfil = _perfil_ou_404(perfil_id)
        assert perfil.id is not None
        meio = request.form.get("meio", "")
        if meio not in _MEIOS:
            abort(400)

        contexto = ContextoConsulta(
            assunto=request.form.get("assunto", "").strip(),
            meio=meio,  # type: ignore[arg-type]
            objetivo=request.form.get("objetivo", "").strip(),
            interessa=_lista_de_csv(request.form.get("interessa", "")),
            evitar=_lista_de_csv(request.form.get("evitar", "")),
            livre=request.form.get("livre", "").strip(),
        )

        pasta_navegador = caminho_banco.parent / "navegador"
        caminho_fontes = caminho_banco.parent.parent / "fontes.yaml"
        agora = datetime.now(UTC).isoformat()
        with httpx.Client(timeout=120.0) as cliente_http:
            consulta_mod.preparar(
                conexao=_conn(),
                cliente_llm=_cliente_llm(),
                cliente_http=cliente_http,
                perfil_id=perfil.id,
                contexto=contexto,
                limiares=limiares,
                caminho_fontes=caminho_fontes,
                caminho_sentinela=caminho_banco.parent / "PARE",
                abrir_pagina=abrir_pagina_playwright,
                pasta_navegador=pasta_navegador,
                agora=agora,
            )
        return redirect(url_for("menu_contato", perfil_id=perfil_id))

    @app.route("/menu")
    def menu_lista() -> str:
        conn = _conn()
        hoje = datetime.now(UTC).date().isoformat()
        com_menu: list[Perfil] = []
        for perfil in perfis.listar_ativos(conn):
            assert perfil.id is not None
            if assunto_contato.listar_do_dia(conn, perfil.id, hoje):
                com_menu.append(perfil)
        return render_template("menu.html", modo="lista", perfis=com_menu)

    @app.route("/menu/<int:perfil_id>")
    def menu_contato(perfil_id: int) -> str:
        conn = _conn()
        perfil = _perfil_ou_404(perfil_id)
        hoje = datetime.now(UTC).date().isoformat()
        registros = assunto_contato.listar_do_dia(conn, perfil_id, hoje)

        conectores = _com_assunto([r for r in registros if r.tipo == "conector" and r.status == "novo"])
        viaveis = _com_assunto(
            [r for r in registros if r.tipo == "viavel_com_esforco" and r.status == "novo"]
        )
        descartados = _com_assunto([r for r in registros if r.status == "descartado"])

        return render_template(
            "menu.html",
            modo="contato",
            perfil=perfil,
            conectores=conectores,
            viaveis=viaveis,
            descartados=descartados,
            motivos=_MOTIVOS,
        )

    @app.route("/menu/<int:perfil_id>/usei/<int:ac_id>", methods=["POST"])
    def marcar_usado_rota(perfil_id: int, ac_id: int) -> Response:
        conn = _conn()
        assunto_contato.marcar_usado(conn, ac_id)
        conn.commit()
        return redirect(url_for("menu_contato", perfil_id=perfil_id))

    @app.route("/menu/<int:perfil_id>/nao-serve/<int:ac_id>", methods=["POST"])
    def marcar_nao_serve_rota(perfil_id: int, ac_id: int) -> Response:
        conn = _conn()
        motivo = request.form.get("motivo", "")
        assunto_contato.marcar_nao_serve(conn, ac_id, motivo)
        conn.commit()
        return redirect(url_for("menu_contato", perfil_id=perfil_id))

    def _validar_link(link: str) -> bool:
        return link.startswith("http://") or link.startswith("https://")

    @app.route("/contatos/<int:perfil_id>/redes-sociais/adicionar", methods=["POST"])
    def adicionar_rede_social_contato(perfil_id: int) -> Response:
        conn = _conn()
        _perfil_ou_404(perfil_id)
        rede = request.form.get("rede", "").strip()
        link = request.form.get("link", "").strip()
        if rede and link and _validar_link(link):
            redes_sociais.inserir(conn, perfil_id, rede, link, datetime.now(UTC).isoformat())
            conn.commit()
        return redirect(url_for("ficha", perfil_id=perfil_id))

    @app.route("/contatos/<int:perfil_id>/redes-sociais/<int:rede_social_id>/remover", methods=["POST"])
    def remover_rede_social_contato(perfil_id: int, rede_social_id: int) -> Response:
        conn = _conn()
        _perfil_ou_404(perfil_id)
        redes_sociais.remover(conn, rede_social_id)
        conn.commit()
        return redirect(url_for("ficha", perfil_id=perfil_id))

    @app.route("/contatos/<int:perfil_id>/redes-sociais/buscar", methods=["POST"])
    def buscar_rede_social_contato(perfil_id: int) -> str:
        from agente_nw.coleta.capturas.playwright_backend import PaginaPlaywright

        perfil = _perfil_ou_404(perfil_id)
        rede = request.form.get("rede", "").strip().lower()
        if rede not in busca.REDES_SUPORTADAS:
            abort(400)

        pasta_rede = caminho_banco.parent / "navegador" / rede
        pagina = PaginaPlaywright(pasta_rede, headless=False)
        try:
            resultado = busca.buscar(pagina, rede, perfil.nome, perfil.empresa)
        finally:
            pagina.fechar()

        return _renderizar_ficha(perfil_id, rede_busca=rede, resultado_busca=resultado)

    @app.route("/eu")
    def eu() -> str:
        conn = _conn()
        usuario = _usuario_ou_none()
        if usuario is None:
            return _sem_usuario()
        assert usuario.id is not None
        redes = redes_sociais.listar_por_perfil(conn, usuario.id)
        return render_template("eu.html", usuario=usuario, redes=redes)

    @app.route("/eu/redes-sociais/adicionar", methods=["POST"])
    def adicionar_rede_social_usuario() -> Response:
        conn = _conn()
        usuario = _usuario_ou_none()
        if usuario is None:
            abort(400)
        assert usuario.id is not None
        rede = request.form.get("rede", "").strip()
        link = request.form.get("link", "").strip()
        if rede and link and _validar_link(link):
            redes_sociais.inserir(conn, usuario.id, rede, link, datetime.now(UTC).isoformat())
            conn.commit()
        return redirect(url_for("eu"))

    @app.route("/eu/redes-sociais/<int:rede_social_id>/remover", methods=["POST"])
    def remover_rede_social_usuario(rede_social_id: int) -> Response:
        conn = _conn()
        redes_sociais.remover(conn, rede_social_id)
        conn.commit()
        return redirect(url_for("eu"))

    @app.route("/temas")
    def temas_lista() -> str:
        conn = _conn()
        usuario = _usuario_ou_none()
        if usuario is None:
            return _sem_usuario()
        assert usuario.id is not None
        vinculos = {vinculo.tema_id: vinculo for vinculo in perfil_tema.listar_por_perfil(conn, usuario.id)}

        confirmados: list[tuple[Tema, PerfilTema]] = []
        pendentes: list[tuple[Tema, PerfilTema]] = []
        for tema in queries_temas.listar(conn):
            assert tema.id is not None
            vinculo = vinculos.get(tema.id)
            if vinculo is None:
                continue
            if vinculo.confirmado:
                confirmados.append((tema, vinculo))
            else:
                pendentes.append((tema, vinculo))

        return render_template("temas.html", confirmados=confirmados, pendentes=pendentes, niveis=_NIVEIS)

    @app.route("/temas/<int:tema_id>/atualizar", methods=["POST"])
    def atualizar_tema(tema_id: int) -> Response:
        conn = _conn()
        tema = queries_temas.obter_por_id(conn, tema_id)
        if tema is None:
            abort(404)
        descricao = request.form.get("descricao", "").strip()
        sinonimos = [s.strip() for s in request.form.get("sinonimos", "").split(",") if s.strip()]
        queries_temas.atualizar(conn, tema_id, descricao, sinonimos)
        vetor = _cliente_llm().embeddar([f"{tema.nome}: {descricao}"])[0]
        queries_temas.gravar_embedding(conn, tema_id, vetor)
        conn.commit()
        return redirect(url_for("temas_lista"))

    @app.route("/temas/<int:tema_id>/nivel", methods=["POST"])
    def atualizar_nivel_tema(tema_id: int) -> Response:
        conn = _conn()
        usuario = _usuario_ou_none()
        if usuario is None:
            abort(400)
        assert usuario.id is not None
        nivel_bruto = request.form.get("nivel", "")
        if nivel_bruto not in _NIVEIS:
            abort(400)
        perfil_tema.atualizar_nivel(conn, usuario.id, tema_id, nivel_bruto)
        conn.commit()
        return redirect(url_for("temas_lista"))

    @app.route("/temas/<int:tema_id>/confirmar", methods=["POST"])
    def confirmar_tema_pendente(tema_id: int) -> Response:
        conn = _conn()
        usuario = _usuario_ou_none()
        if usuario is None:
            abort(400)
        assert usuario.id is not None
        perfil_tema.confirmar(conn, usuario.id, tema_id)
        conn.commit()
        return redirect(url_for("temas_lista"))

    def _monta_tema_usuario_do_form(prefixo: str) -> TemaUsuario | None:
        nome = request.form.get(f"{prefixo}nome", "").strip()
        if not nome:
            return None
        descricao = request.form.get(f"{prefixo}descricao", "").strip()
        nivel_bruto = request.form.get(f"{prefixo}nivel", "").strip()
        if nivel_bruto not in _NIVEIS:
            raise ValueError(f"nível inválido: '{nivel_bruto}'")
        peso_bruto = request.form.get(f"{prefixo}peso", "3").strip() or "3"
        try:
            peso = int(peso_bruto)
        except ValueError as erro:
            raise ValueError(f"peso inválido: '{peso_bruto}'") from erro
        return TemaUsuario(
            nome=nome,
            descricao=descricao,
            nivel=nivel_bruto,
            peso=peso,
            sinonimos=[],
        )

    @app.route("/eu/configurar", methods=["POST"])
    def configurar_perfil_usuario() -> Response | str:
        nome = request.form.get("nome", "").strip()
        if not nome:
            return _sem_usuario(erro="Nome é obrigatório.")
        temas: list[TemaUsuario] = []
        try:
            for i in range(20):
                tema = _monta_tema_usuario_do_form(f"tema_{i}_")
                if tema is not None:
                    temas.append(tema)
        except (ValueError, ValidationError) as erro:
            return _sem_usuario(erro=str(erro))
        if not temas:
            return _sem_usuario(erro="Cadastre ao menos um tema.")

        agora = datetime.now(UTC).isoformat()
        configurador.salvar_perfil_usuario(_conn(), _cliente_llm(), nome, temas, agora)
        return redirect(url_for("eu"))

    @app.route("/temas/novo", methods=["POST"])
    def adicionar_tema_usuario() -> Response:
        usuario = _usuario_ou_none()
        if usuario is None:
            abort(400)
        assert usuario.id is not None
        try:
            tema = _monta_tema_usuario_do_form("tema_")
        except (ValueError, ValidationError):
            abort(400)
        if tema is None:
            abort(400)
        agora = datetime.now(UTC).isoformat()
        configurador.adicionar_tema_do_usuario(_conn(), _cliente_llm(), usuario.id, tema, agora)
        return redirect(url_for("temas_lista"))

    @app.route("/temas/<int:tema_id>/remover-do-usuario", methods=["POST"])
    def remover_tema_do_usuario(tema_id: int) -> Response:
        usuario = _usuario_ou_none()
        if usuario is None:
            abort(400)
        assert usuario.id is not None
        configurador.remover_tema_do_usuario(_conn(), usuario.id, tema_id)
        return redirect(url_for("temas_lista"))

    return app
