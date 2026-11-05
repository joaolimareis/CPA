"""Registro de acessos: quem entrou, quando e em quais páginas (para a CPA acompanhar)."""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from cpa.config import get_settings

ARQUIVO = "acessos.jsonl"


def registrar(evento: str, login: str, detalhe: str = "") -> None:
    try:
        pasta = get_settings().pasta_dados
        pasta.mkdir(parents=True, exist_ok=True)
        linha = {"data_hora": datetime.now().isoformat(timespec="seconds"), "evento": evento,
                 "usuario": login, "detalhe": detalhe}
        with open(pasta / ARQUIVO, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    except OSError:
        pass  # o registro nunca pode impedir o uso do sistema


def ler(limite: int = 2000) -> pd.DataFrame:
    caminho = get_settings().pasta_dados / ARQUIVO
    if not caminho.exists():
        return pd.DataFrame(columns=["data_hora", "evento", "usuario", "detalhe"])
    linhas = caminho.read_text(encoding="utf-8").splitlines()[-limite:]
    registros = []
    for linha in linhas:
        try:
            registros.append(json.loads(linha))
        except json.JSONDecodeError:
            continue
    df = pd.DataFrame(registros)
    return df.iloc[::-1].reset_index(drop=True) if not df.empty else df
