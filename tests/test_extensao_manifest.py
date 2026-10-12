from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from agente_nw.ponte import ID_EXTENSAO

PASTA = Path(__file__).resolve().parent.parent / "extensao"
REDES = {
    "https://*.linkedin.com/*",
    "https://*.instagram.com/*",
    "https://*.facebook.com/*",
    "https://*.x.com/*",
}
ORIGEM_PONTE = "http://127.0.0.1:8766/*"


@pytest.fixture
def manifest() -> dict[str, Any]:
    dados: dict[str, Any] = json.loads((PASTA / "manifest.json").read_text(encoding="utf-8"))
    return dados


def test_manifest_v3_com_chave_fixa(manifest: dict[str, Any]) -> None:
    assert manifest["manifest_version"] == 3
    assert manifest["key"]


def test_id_da_extensao_bate_com_a_chave_do_manifest(manifest: dict[str, Any]) -> None:
    der = base64.b64decode(manifest["key"])
    hexa = hashlib.sha256(der).hexdigest()[:32]
    identificador = "".join(chr(ord("a") + int(c, 16)) for c in hexa)

    assert identificador == ID_EXTENSAO


def test_host_permissions_so_nas_quatro_redes(manifest: dict[str, Any]) -> None:
    assert set(manifest["host_permissions"]) == REDES


def test_permissoes_minimas(manifest: dict[str, Any]) -> None:
    assert set(manifest["permissions"]) == {"tabs", "scripting", "activeTab"}


def test_so_a_pagina_da_ponte_conversa_com_a_extensao(manifest: dict[str, Any]) -> None:
    assert manifest["externally_connectable"] == {"matches": [ORIGEM_PONTE]}
    (script,) = manifest["content_scripts"]
    assert script["matches"] == [ORIGEM_PONTE]


def test_arquivos_citados_no_manifest_existem(manifest: dict[str, Any]) -> None:
    citados = [manifest["background"]["service_worker"], manifest["icons"]["128"]]
    citados += [arquivo for script in manifest["content_scripts"] for arquivo in script["js"]]

    for arquivo in citados:
        assert (PASTA / arquivo).is_file(), arquivo
    assert (PASTA / "conteudo.js").is_file()


def test_background_so_conhece_o_conjunto_fixo_de_acoes() -> None:
    codigo = (PASTA / "background.js").read_text(encoding="utf-8")

    for acao in ("ola", "abrir", "estado", "rolar", "links", "fechar"):
        assert f'case "{acao}"' in codigo
    assert "eval(" not in codigo
    assert "new Function" not in codigo
