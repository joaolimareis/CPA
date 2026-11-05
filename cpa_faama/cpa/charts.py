"""Gráficos (Plotly) com o padrão visual do sistema."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from cpa.processing import ORDEM_GRUPOS

AZUL = "#003B6F"
CORES_GRUPO = {"Favorável": "#2E7D32", "Neutro": "#B0B7C3", "Desfavorável": "#C62828", "Não se aplica": "#E3E6EA"}
FONTE = dict(family="Public Sans, Segoe UI, Arial, sans-serif", size=12, color="#13263B")


def rotulo_curto(texto: str, limite: int = 60) -> str:
    texto = str(texto)
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def _layout(fig: go.Figure, altura: int, legenda: bool = False) -> go.Figure:
    fig.update_layout(
        height=altura, template="plotly_white", font=FONTE,
        margin=dict(l=10, r=20, t=30 if legenda else 10, b=10),
        showlegend=legenda, separators=",.",
        legend=dict(orientation="h", y=1.08, x=0, title=None),
        hoverlabel=dict(bgcolor="white"),
    )
    return fig


def vazio(mensagem: str = "Sem dados para os filtros selecionados", altura: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=mensagem, showarrow=False, font=dict(size=14, color="#6B7280"))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _layout(fig, altura)


def barras_percentual(resumo: pd.DataFrame, categoria: str, valor: str = "pct_favoravel",
                      ordenar_por: str | None = None, altura: int | None = None,
                      cor: str = AZUL) -> go.Figure:
    dados = resumo.dropna(subset=[valor])
    if dados.empty:
        return vazio()
    dados = dados.sort_values(ordenar_por or valor, ascending=True)
    rotulos = dados[categoria].map(rotulo_curto)
    fig = go.Figure(go.Bar(
        x=dados[valor], y=rotulos, orientation="h", marker_color=cor,
        text=dados[valor].map(lambda v: f"{v:.1%}".replace(".", ",")), textposition="outside",
        customdata=dados[[categoria, "questionarios"]].to_numpy(),
        hovertemplate="<b>%{customdata[0]}</b><br>%{x:.1%}<br>%{customdata[1]} respondentes<extra></extra>",
    ))
    fig.update_xaxes(visible=False, range=[0, 1.12])
    fig.update_yaxes(title=None)
    return _layout(fig, altura or max(260, 34 * len(dados) + 40))


def barras_distribuicao(dist: pd.DataFrame, categoria: str, altura: int | None = None) -> go.Figure:
    if dist.empty:
        return vazio()
    dados = dist.copy()
    fav = dados[dados["GRUPO"] == "Favorável"].set_index(categoria)["pct"]
    ordem = dados[categoria].drop_duplicates().sort_values(key=lambda s: s.map(fav).fillna(0)).tolist()
    dados["rotulo"] = dados[categoria].map(rotulo_curto)
    fig = px.bar(
        dados, x="pct", y="rotulo", color="GRUPO", orientation="h",
        color_discrete_map=CORES_GRUPO,
        category_orders={"GRUPO": ORDEM_GRUPOS, "rotulo": [rotulo_curto(o) for o in ordem]},
        custom_data=[categoria, "respostas"],
        text=dados["pct"].map(lambda v: f"{v:.0%}" if v >= 0.06 else ""),
    )
    fig.update_traces(textposition="inside", insidetextanchor="middle", textfont_color="white",
                      hovertemplate="<b>%{customdata[0]}</b><br>%{x:.1%} · %{customdata[1]} respostas<extra></extra>")
    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(title=None)
    fig.update_layout(barmode="stack")
    return _layout(fig, altura or max(260, 36 * len(ordem) + 70), legenda=True)


def rosca(ind, altura: int = 300) -> go.Figure:
    valores = [ind.pct_favoravel, ind.pct_neutro, ind.pct_desfavoravel]
    if any(pd.isna(v) for v in valores):
        return vazio(altura=altura)
    rotulos = ["Favorável", "Neutro", "Desfavorável"]
    fig = go.Figure(go.Pie(
        labels=rotulos, values=valores, hole=0.62, sort=False,
        marker_colors=[CORES_GRUPO[r] for r in rotulos], textinfo="percent",
        hovertemplate="%{label}: %{percent}<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{ind.pct_favoravel:.0%}</b><br>favorável", showarrow=False, font=dict(size=18, color=AZUL))
    return _layout(fig, altura, legenda=True)


def evolucao(resumo: pd.DataFrame, serie: str = "AVALIACAO", altura: int = 300) -> go.Figure:
    dados = resumo.dropna(subset=["pct_favoravel"])
    if dados.empty or dados["SEMESTRE"].nunique() < 2:
        return vazio("A evolução aparece quando houver mais de um semestre", altura)
    fig = px.line(dados.sort_values("SEMESTRE"), x="SEMESTRE", y="pct_favoravel", color=serie,
                  markers=True, color_discrete_sequence=[AZUL, "#F18F01", "#2E86AB", "#8E5BA8"])
    fig.update_traces(hovertemplate="%{x}: %{y:.1%}<extra></extra>")
    fig.update_yaxes(tickformat=".0%", title=None)
    fig.update_xaxes(title=None, type="category")
    return _layout(fig, altura, legenda=True)


def mapa_calor(tabela: pd.DataFrame, altura: int | None = None) -> go.Figure:
    if tabela.empty or tabela.notna().sum().sum() == 0:
        return vazio("Sem células com respondentes suficientes")
    tabela = tabela.copy()
    tabela.columns = [rotulo_curto(c, 38) for c in tabela.columns]
    texto = tabela.map(lambda v: "" if pd.isna(v) else f"{v:.0%}")
    fig = go.Figure(go.Heatmap(
        z=tabela.values, x=tabela.columns, y=tabela.index, text=texto.values, texttemplate="%{text}",
        colorscale=[[0, "#C62828"], [0.6, "#F5E6A8"], [1, "#2E7D32"]], zmin=0.5, zmax=1,
        hovertemplate="%{y}<br>%{x}<br>%{z:.1%}<extra></extra>", colorbar=dict(tickformat=".0%"),
    ))
    fig.update_xaxes(tickangle=-35)
    return _layout(fig, altura or max(320, 28 * len(tabela) + 160))


def termos(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return vazio("Sem comentários suficientes")
    dados = df.sort_values("ocorrencias")
    fig = go.Figure(go.Bar(x=dados["ocorrencias"], y=dados["termo"], orientation="h", marker_color="#2E86AB",
                           hovertemplate="%{y}: %{x} ocorrências<extra></extra>"))
    fig.update_xaxes(title=None)
    return _layout(fig, max(260, 22 * len(dados) + 40))


def barras_quantidade(resumo: pd.DataFrame, categoria: str, valor: str = "questionarios",
                      altura: int | None = None) -> go.Figure:
    if resumo.empty:
        return vazio()
    dados = resumo.sort_values(valor, ascending=True)
    fig = go.Figure(go.Bar(
        x=dados[valor], y=dados[categoria].map(rotulo_curto), orientation="h", marker_color="#2E86AB",
        text=dados[valor].map(lambda v: f"{int(v):,}".replace(",", ".")), textposition="outside",
        hovertemplate="%{y}: %{x} questionários<extra></extra>",
    ))
    fig.update_xaxes(visible=False, range=[0, dados[valor].max() * 1.15])
    return _layout(fig, altura or max(260, 34 * len(dados) + 40))


COR_META_OK, COR_META_PERTO, COR_META_LONGE = "#2E7D32", "#C98A1B", "#C62828"


def cor_meta(valor: float, meta: float) -> str:
    """Verde: atingiu a meta. Amarelo: passou da metade da meta. Vermelho: abaixo da metade."""
    if valor >= meta:
        return COR_META_OK
    return COR_META_PERTO if valor >= meta / 2 else COR_META_LONGE


def termometro(dados: pd.DataFrame, categoria: str, meta: float, vertical: bool = True,
               altura: int | None = None) -> go.Figure:
    """Termômetro de adesão: tubo cinza de 0 a 100%, preenchido até a adesão, com a linha da meta."""
    if dados.empty:
        return vazio()
    d = dados.sort_values("taxa_adesao", ascending=not vertical)
    nomes = d[categoria].map(lambda t: rotulo_curto(t, 28 if vertical else 50)).tolist()
    valores = d["taxa_adesao"].fillna(0).tolist()
    texto = [f"{v:.0%}<br>{int(r)} de {int(m)}" if vertical else f"{v:.0%}  ({int(r)} de {int(m)})"
             for v, r, m in zip(valores, d["ALUNOS_RESPONDERAM"], d["ALUNOS_MATRICULADOS"])]
    cores = [cor_meta(v, meta) for v in valores]
    eixo = dict(x=nomes, y=[1] * len(nomes)) if vertical else dict(y=nomes, x=[1] * len(nomes))
    eixo_v = dict(x=nomes, y=valores) if vertical else dict(y=nomes, x=valores)
    fig = go.Figure()
    fig.add_bar(**eixo, orientation="v" if vertical else "h", marker_color="#E6EBF1", width=0.55,
                hoverinfo="skip", showlegend=False)
    fig.add_bar(**eixo_v, orientation="v" if vertical else "h", marker_color=cores, width=0.55, text=texto,
                textposition="outside", cliponaxis=False, showlegend=False,
                customdata=d[[categoria, "ALUNOS_RESPONDERAM", "ALUNOS_MATRICULADOS"]].to_numpy(),
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} de %{customdata[2]} alunos<extra></extra>")
    linha_meta = dict(line_dash="dash", line_color="#13263B", line_width=1.5,
                      annotation_text=f"meta {meta:.0%}", annotation_font_size=11)
    if vertical:
        fig.add_hline(y=meta, annotation_position="top left", **linha_meta)
        fig.update_yaxes(range=[0, 1.18], tickformat=".0%", showgrid=False, title=None)
        fig.update_xaxes(title=None, tickfont=dict(size=12))
    else:
        fig.add_vline(x=meta, annotation_position="top", **linha_meta)
        fig.update_xaxes(range=[0, 1.25], tickformat=".0%", showgrid=False, title=None)
        fig.update_yaxes(title=None, tickfont=dict(size=11))
    fig.update_layout(barmode="overlay", bargap=0.35)
    alt = altura or (380 if vertical else max(260, 38 * len(nomes) + 70))
    return _layout(fig, alt)
