from __future__ import annotations

import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from agente_nw.nucleo.database import conexao as modulo_conexao

RETENCAO_DIAS = 7


def fazer_backup(conexao: sqlite3.Connection, pasta: Path, agora: datetime | None = None) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    data = (agora or datetime.now()).strftime("%Y-%m-%d")
    destino = pasta / f"agente_{data}.db"

    destino_conexao = modulo_conexao.abrir(destino)
    try:
        conexao.backup(destino_conexao)
    finally:
        destino_conexao.close()

    apagar_antigos(pasta)
    return destino


def apagar_antigos(pasta: Path, retencao_dias: int = RETENCAO_DIAS) -> list[Path]:
    limite = time.time() - retencao_dias * 86400
    apagados = []
    for arquivo in pasta.glob("agente_*.db"):
        if arquivo.stat().st_mtime < limite:
            arquivo.unlink()
            apagados.append(arquivo)
    return apagados


def backup_mais_recente(pasta: Path) -> Path | None:
    if not pasta.exists():
        return None
    arquivos = sorted(pasta.glob("agente_*.db"))
    return arquivos[-1] if arquivos else None


def copiar_para(origem: Path, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origem, destino)
    return destino


def restaurar(arquivo_backup: Path, caminho_banco: Path) -> Path:
    caminho_banco.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(arquivo_backup, caminho_banco)
    return caminho_banco
