"""Validação da avaliação docente: o que foi aceito e o que foi descartado (e por quê)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from cpa.processing import MOTIVO_REPETIDA, MOTIVO_SEMESTRE_ANTERIOR


def _contar(df: pd.DataFrame, por: list[str], nome: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=por + [nome])
    return df.groupby(por, dropna=False)["ID_RESPONDENTE"].nunique().rename(nome).reset_index()


def resumo(validas: pd.DataFrame, descartes: pd.DataFrame, por: list[str]) -> pd.DataFrame:
    """Avaliações recebidas, aceitas e descartadas por motivo (contadas em questionários)."""
    partes = [_contar(validas, por, "validas")]
    if not descartes.empty:
        partes.append(_contar(descartes[descartes["MOTIVO_DESCARTE"] == MOTIVO_SEMESTRE_ANTERIOR], por, "semestre_anterior"))
        partes.append(_contar(descartes[descartes["MOTIVO_DESCARTE"] == MOTIVO_REPETIDA], por, "repetidas"))
    out = partes[0]
    for p in partes[1:]:
        out = out.merge(p, on=por, how="outer")
    for c in ("validas", "semestre_anterior", "repetidas"):
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int) if c in out else 0
    out["recebidas"] = out["validas"] + out["semestre_anterior"] + out["repetidas"]
    out["pct_validas"] = out["validas"] / out["recebidas"].replace(0, np.nan)
    out["pct_descartadas"] = 1 - out["pct_validas"]
    return out.sort_values("recebidas", ascending=False).reset_index(drop=True)


def professores_anteriores(descartes: pd.DataFrame) -> pd.DataFrame:
    """Professores/disciplinas de semestres anteriores que os alunos avaliaram."""
    d = descartes[descartes["MOTIVO_DESCARTE"] == MOTIVO_SEMESTRE_ANTERIOR] if not descartes.empty else descartes
    if d.empty:
        return pd.DataFrame(columns=["NOME_PROFESSOR", "NOME_DISCIPLINA", "SEMESTRE_DISCIPLINA", "avaliacoes"])
    return (d.groupby(["NOME_PROFESSOR", "NOME_DISCIPLINA", "SEMESTRE_DISCIPLINA"], dropna=False)["ID_RESPONDENTE"]
            .nunique().rename("avaliacoes").reset_index().sort_values("avaliacoes", ascending=False))


def professores_fora_do_semestre(validas: pd.DataFrame, descartes: pd.DataFrame) -> pd.DataFrame:
    """Professores que só receberam avaliações descartadas: não têm disciplina no semestre selecionado."""
    d = descartes[descartes["MOTIVO_DESCARTE"] == MOTIVO_SEMESTRE_ANTERIOR] if not descartes.empty else descartes
    if d.empty:
        return pd.DataFrame(columns=["NOME_PROFESSOR", "avaliacoes_descartadas", "ultimo_semestre_avaliado"])
    ativos = set(validas["CODPROF"].dropna()) if not validas.empty else set()
    fora = d[~d["CODPROF"].isin(ativos)]
    if fora.empty:
        return pd.DataFrame(columns=["NOME_PROFESSOR", "avaliacoes_descartadas", "ultimo_semestre_avaliado"])
    return (fora.groupby("NOME_PROFESSOR", dropna=False)
            .agg(avaliacoes_descartadas=("ID_RESPONDENTE", "nunique"),
                 ultimo_semestre_avaliado=("SEMESTRE_DISCIPLINA", "max"))
            .reset_index().sort_values("avaliacoes_descartadas", ascending=False))


def detalhe_professor(validas: pd.DataFrame, descartes: pd.DataFrame, professor: str) -> pd.DataFrame:
    """Disciplinas de um professor: semestre da disciplina e situação de cada avaliação."""
    v = validas[validas["NOME_PROFESSOR"] == professor].assign(SITUACAO="Aceita")
    d = descartes[descartes["NOME_PROFESSOR"] == professor].rename(columns={"MOTIVO_DESCARTE": "SITUACAO"}) \
        if not descartes.empty else descartes
    juntos = pd.concat([v, d], ignore_index=True)
    if juntos.empty:
        return pd.DataFrame()
    if "SEMESTRE_DISCIPLINA" not in juntos:
        juntos["SEMESTRE_DISCIPLINA"] = pd.NA
    juntos["SEMESTRE_DISCIPLINA"] = juntos["SEMESTRE_DISCIPLINA"].fillna(juntos["SEMESTRE"])
    return (juntos.groupby(["NOME_DISCIPLINA", "NOME_CURSO", "SEMESTRE_DISCIPLINA", "SITUACAO"], dropna=False)
            ["ID_RESPONDENTE"].nunique().rename("avaliacoes").reset_index()
            .sort_values(["SEMESTRE_DISCIPLINA", "NOME_DISCIPLINA"], ascending=[False, True]))
