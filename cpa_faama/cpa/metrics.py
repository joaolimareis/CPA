"""Indicadores da avaliação: as mesmas medidas do Power BI, mais algumas análises extras."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd



@dataclass(frozen=True)
class Indicadores:
    questionarios: int
    respostas_validas: int
    pct_favoravel: float
    pct_neutro: float
    pct_desfavoravel: float
    nota_media: float
    nota_global: float
    pct_indicaria: float
    comentarios: int


def _div(a, b):
    return a / b if b else np.nan


def indicadores(df: pd.DataFrame) -> Indicadores:
    validas = int(df["VALIDA"].sum())
    nota_global = df.loc[df["ESCALA"].eq("Nota global").fillna(False), "NOTA"]
    indicacao = df[df["ESCALA"].eq("Indicação").fillna(False)]
    return Indicadores(
        questionarios=int(df["ID_RESPONDENTE"].nunique()),
        respostas_validas=validas,
        pct_favoravel=_div(df["FAVORAVEL"].sum(), validas),
        pct_neutro=_div(df["NEUTRO"].sum(), validas),
        pct_desfavoravel=_div(df["DESFAVORAVEL"].sum(), validas),
        nota_media=float(df["NOTA"].mean()) if df["NOTA"].notna().any() else np.nan,
        nota_global=float(nota_global.mean()) if nota_global.notna().any() else np.nan,
        pct_indicaria=float(indicacao["FAVORAVEL"].mean()) if len(indicacao) else np.nan,
        comentarios=int(df["E_COMENTARIO"].sum()),
    )


def wilson_inferior(sucessos, total, z: float = 1.96) -> np.ndarray:
    """Limite inferior do intervalo de confiança de Wilson (95%).

    Evita que um professor com 3 respostas favoráveis em 3 (100%) fique à frente de
    outro com 95 em 100: o índice desconta a incerteza das amostras pequenas.
    """
    s = np.asarray(sucessos, dtype=float)
    n = np.asarray(total, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = s / n
        denominador = 1 + z ** 2 / n
        centro = p + z ** 2 / (2 * n)
        margem = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2))
        resultado = (centro - margem) / denominador
    return np.where(n > 0, np.clip(resultado, 0, 1), np.nan)


def resumo_por(df: pd.DataFrame, por: list[str], min_respondentes: int | None = None) -> pd.DataFrame:
    """Indicadores agrupados. Grupos abaixo do mínimo de respondentes ficam sem resultado."""
    if df.empty:
        return pd.DataFrame(columns=por + ["questionarios", "pct_favoravel"])
    g = df.groupby(por, dropna=False, observed=True)
    out = g.agg(
        questionarios=("ID_RESPONDENTE", "nunique"),
        respostas_validas=("VALIDA", "sum"),
        favoraveis=("FAVORAVEL", "sum"),
        neutras=("NEUTRO", "sum"),
        desfavoraveis=("DESFAVORAVEL", "sum"),
        nota_media=("NOTA", "mean"),
        comentarios=("E_COMENTARIO", "sum"),
    ).reset_index()

    nota = (df[df["ESCALA"].eq("Nota global").fillna(False)]
            .groupby(por, dropna=False, observed=True)["NOTA"].mean().rename("nota_global"))
    indic = (df[df["ESCALA"].eq("Indicação").fillna(False)]
             .groupby(por, dropna=False, observed=True)["FAVORAVEL"].mean().rename("pct_indicaria"))
    out = out.merge(nota.reset_index(), on=por, how="left").merge(indic.reset_index(), on=por, how="left")

    # Uma pessoa = um voto: cada questionário é classificado como insatisfeito quando tem
    # mais respostas desfavoráveis do que favoráveis.
    por_q = (df[df["VALIDA"] == 1].groupby(por + ["ID_RESPONDENTE"], dropna=False, observed=True)
             [["FAVORAVEL", "DESFAVORAVEL"]].sum().reset_index())
    por_q["insatisfeito"] = (por_q["DESFAVORAVEL"] > por_q["FAVORAVEL"]).astype(int)
    pessoas = (por_q.groupby(por, dropna=False, observed=True)
               .agg(avaliacoes_insatisfeitas=("insatisfeito", "sum"), avaliacoes_com_nota=("insatisfeito", "size"))
               .reset_index())
    out = out.merge(pessoas, on=por, how="left")
    out[["avaliacoes_insatisfeitas", "avaliacoes_com_nota"]] = (
        out[["avaliacoes_insatisfeitas", "avaliacoes_com_nota"]].fillna(0).astype(int))
    n_pessoas = out["avaliacoes_com_nota"].replace(0, np.nan)
    out["pct_insatisfeitos"] = out["avaliacoes_insatisfeitas"] / n_pessoas
    out["indice_alerta"] = wilson_inferior(out["avaliacoes_insatisfeitas"], out["avaliacoes_com_nota"])

    v = out["respostas_validas"].replace(0, np.nan)
    out["pct_favoravel"] = out["favoraveis"] / v
    out["pct_neutro"] = out["neutras"] / v
    out["pct_desfavoravel"] = out["desfavoraveis"] / v
    out["indice_confianca"] = wilson_inferior(out["favoraveis"], out["respostas_validas"])

    out["protegido"] = False
    sensiveis = ["pct_favoravel", "pct_neutro", "pct_desfavoravel", "indice_confianca",
                 "nota_media", "nota_global", "pct_indicaria", "pct_insatisfeitos", "indice_alerta"]
    if min_respondentes:
        out["protegido"] = out["questionarios"] < min_respondentes
        out.loc[out["protegido"], sensiveis] = np.nan
    out[sensiveis] = out[sensiveis].apply(pd.to_numeric, errors="coerce")
    return out


def distribuicao(df: pd.DataFrame, por: str, min_respondentes: int | None = None) -> pd.DataFrame:
    """Percentual de Favorável / Neutro / Desfavorável dentro de cada categoria."""
    validas = df[df["VALIDA"] == 1]
    if validas.empty:
        return pd.DataFrame(columns=[por, "GRUPO", "respostas", "pct"])
    contagem = validas.groupby([por, "GRUPO"], observed=True).size().rename("respostas").reset_index()
    contagem["pct"] = contagem["respostas"] / contagem.groupby(por)["respostas"].transform("sum")
    if min_respondentes:
        n = df.groupby(por, observed=True)["ID_RESPONDENTE"].nunique()
        permitidos = n[n >= min_respondentes].index
        contagem = contagem[contagem[por].isin(permitidos)]
    return contagem


def mapa_calor(df: pd.DataFrame, linhas: str, colunas: str, min_respondentes: int) -> pd.DataFrame:
    """Tabela linhas × colunas com % favorável; células com poucos respondentes ficam vazias."""
    r = resumo_por(df, [linhas, colunas], min_respondentes)
    if r.empty:
        return pd.DataFrame()
    return r.pivot(index=linhas, columns=colunas, values="pct_favoravel")


STOPWORDS = set("""
a à ao aos as às até com como da das de dela dele deles demais depois do dos e é ela elas ele eles em entre era
essa essas esse esses esta está estão estas este estes eu foi for foram há isso isto já la lhe mais mas me mesmo
meu minha muito muita na nas não nem no nos nós nossa nosso num numa o os ou para pela pelas pelo pelos por
porque pois quando que quem se sem ser seu sua são só também tem têm ter tão toda todas todo todos tu um uma
umas uns vai você vocês aula aulas professor professora prof disciplina sempre bem ser sobre pouco forma acho
fazer faz pode poderia gostaria seria tudo coisa coisas ainda alguns algumas mesma assim aqui então ate
""".split())


def termos_frequentes(textos: pd.Series, quantidade: int = 20) -> pd.DataFrame:
    contador: Counter[str] = Counter()
    for texto in textos.dropna():
        palavras = re.findall(r"[a-zà-ú]{3,}", texto.lower())
        contador.update(p for p in palavras if p not in STOPWORDS)
    return pd.DataFrame(contador.most_common(quantidade), columns=["termo", "ocorrencias"])


def pontos_de_atencao(df: pd.DataFrame, por: list[str], min_respondentes: int,
                      limite_desfavoravel: float) -> pd.DataFrame:
    r = resumo_por(df, por, min_respondentes)
    if r.empty:
        return r
    r = r[~r["protegido"] & (r["pct_desfavoravel"] >= limite_desfavoravel)]
    # Ordena pelo índice de alerta: considera quantas PESSOAS estão insatisfeitas e quantas responderam
    return r.sort_values(["indice_alerta", "pct_desfavoravel"], ascending=False)
