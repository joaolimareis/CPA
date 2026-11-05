"""Participação na avaliação: dados agregados por turma (consulta de participação do TOTVS)."""
from __future__ import annotations

import random

import numpy as np
import pandas as pd

from cpa.metrics import wilson_inferior

TEXTO = ["SEMESTRE", "CODPERLET", "NOME_CURSO", "CODTURMA", "NOME_TURMA"]
NUMEROS = ["ALUNOS_MATRICULADOS", "ALUNOS_RESPONDERAM", "ALUNOS_RESP_DOCENTE", "ALUNOS_RESP_INSTITUCIONAL",
           "DOCENTE_ESPERADAS", "DOCENTE_RESPONDIDAS"]


def processar(registros) -> pd.DataFrame:
    df = registros.copy() if isinstance(registros, pd.DataFrame) else pd.DataFrame(list(registros))
    faltando = [c for c in TEXTO + NUMEROS if c not in df.columns]
    if faltando:
        raise ValueError(f"A consulta de participação não trouxe as colunas: {', '.join(faltando)}")
    df = df[TEXTO + NUMEROS].copy()
    for c in TEXTO:
        df[c] = df[c].astype("string").str.strip()
    df["NOME_TURMA"] = df["NOME_TURMA"].fillna(df["CODTURMA"]).fillna("(sem turma)")
    for c in NUMEROS:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df[df["ALUNOS_MATRICULADOS"] > 0].reset_index(drop=True)


def ranking(df: pd.DataFrame, por: list[str], ordenar: str = "indice") -> pd.DataFrame:
    """Taxa de adesão, índice ajustado (Wilson) e completude da avaliação docente.

    `ordenar`: "indice" (padrão, para turmas de tamanhos muito diferentes) ou "taxa_adesao" (cursos).
    """
    if df.empty:
        return pd.DataFrame(columns=por + ["taxa_adesao", "indice"])
    r = df.groupby(por, dropna=False)[NUMEROS].sum().reset_index()
    mat = r["ALUNOS_MATRICULADOS"].replace(0, np.nan)
    r["taxa_adesao"] = r["ALUNOS_RESPONDERAM"] / mat
    r["taxa_docente"] = r["ALUNOS_RESP_DOCENTE"] / mat
    r["taxa_institucional"] = r["ALUNOS_RESP_INSTITUCIONAL"] / mat
    r["indice"] = wilson_inferior(r["ALUNOS_RESPONDERAM"], r["ALUNOS_MATRICULADOS"])
    r["completude"] = r["DOCENTE_RESPONDIDAS"] / r["DOCENTE_ESPERADAS"].replace(0, np.nan)
    # Mais avaliações respondidas do que esperadas indica erro na consulta: não exibimos a completude
    r["inconsistente"] = r["DOCENTE_RESPONDIDAS"] > r["DOCENTE_ESPERADAS"]
    r.loc[r["inconsistente"], "completude"] = np.nan
    r = r.sort_values([ordenar, "ALUNOS_RESPONDERAM"], ascending=False).reset_index(drop=True)
    r.insert(0, "posicao", range(1, len(r) + 1))
    return r


def gerar_demo(semente: int = 7) -> list[dict]:
    rng = random.Random(semente)
    linhas = []
    for semestre in ("2025/2", "2026/1"):
        for curso, turmas in (("Direito", 3), ("Enfermagem", 4), ("Psicologia", 5), ("Pedagogia", 3),
                              ("Análise e Desenvolvimento de Sistemas", 2)):
            for t in range(turmas):
                matriculados = rng.choice([8, 15, 22, 30, 45, 70, 110])
                adesao = rng.uniform(0.2, 0.9)
                responderam = round(matriculados * adesao)
                esperadas = matriculados * rng.randint(5, 9)
                linhas.append({
                    "SEMESTRE": semestre, "CODPERLET": semestre, "NOME_CURSO": curso,
                    "CODTURMA": f"{curso[:3].upper()}{t + 1}", "NOME_TURMA": f"{curso} - {2 * t + 1}º Período",
                    "ALUNOS_MATRICULADOS": matriculados, "ALUNOS_RESPONDERAM": responderam,
                    "ALUNOS_RESP_DOCENTE": round(responderam * 0.95),
                    "ALUNOS_RESP_INSTITUCIONAL": round(responderam * 0.8),
                    "DOCENTE_ESPERADAS": esperadas, "DOCENTE_RESPONDIDAS": round(esperadas * adesao * 0.8),
                })
    return linhas
