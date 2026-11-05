import plotly.express as px
import streamlit as st

from cpa import charts, metrics, participacao, repository, ui
from cpa.config import get_settings

ui.aplicar_estilo()
MIN = get_settings().min_respondentes
df, meta = ui.base_do_usuario()
ui.cabecalho("Histórico", "Como a participação e os resultados evoluem de um semestre para outro", meta)
if df.empty:
    ui.sem_dados()

semestres = sorted(df["SEMESTRE"].dropna().unique())
if len(semestres) < 2:
    st.info("O histórico aparece a partir do segundo semestre com dados.")
st.caption("Semestres com dados: " + ", ".join(semestres) + ". Para incluir semestres anteriores, acrescente os "
           "períodos nas consultas FAAMACPA.6 e FAAMACPA.7 do TOTVS.")


def linha(dados, cor, valor, titulo_y):
    fig = px.line(dados.sort_values("SEMESTRE"), x="SEMESTRE", y=valor, color=cor, markers=True,
                  color_discrete_sequence=[charts.AZUL, "#2E86AB", "#C98A1B", "#3B8B5A", "#8E5BA8", "#B23A48"])
    fig.update_traces(hovertemplate="%{x}: %{y:.1%}<extra>%{fullData.name}</extra>")
    fig.update_yaxes(tickformat=".0%", title=titulo_y, rangemode="tozero")
    fig.update_xaxes(title=None, type="category")
    fig.update_layout(height=360, template="plotly_white", legend_title=None, font=charts.FONTE,
                      legend=dict(orientation="h", y=1.12, x=0), margin=dict(l=10, r=10, t=40, b=10))
    return fig


# ---------- participação ----------
st.subheader("Participação por curso")
if repository.participacao_configurada():
    part, _ = ui.participacao_do_usuario()
    if not part.empty:
        rk = participacao.ranking(part, ["SEMESTRE", "NOME_CURSO"])
        st.plotly_chart(linha(rk, "NOME_CURSO", "taxa_adesao", "Adesão"), width="stretch")
        tabela = rk.pivot(index="NOME_CURSO", columns="SEMESTRE", values="taxa_adesao")
        tabela.index.name = "Curso"
        st.dataframe((tabela * 100).round(1).astype(str).replace("nan", "—") + "%", width="stretch")
    st.caption("Adesão = alunos que responderam ÷ alunos ativos no semestre. O semestre em andamento ainda pode subir.")
else:
    st.info("Configure a consulta de participação para ver a evolução da adesão.")

# ---------- resultados ----------
st.subheader("Respostas favoráveis por tipo de avaliação")
por_tipo = metrics.resumo_por(df, ["SEMESTRE", "AVALIACAO"])
st.plotly_chart(linha(por_tipo, "AVALIACAO", "pct_favoravel", "% favorável"), width="stretch")

st.subheader("Respostas favoráveis por curso")
por_curso = metrics.resumo_por(df, ["SEMESTRE", "NOME_CURSO"], MIN)
tabela = por_curso.pivot(index="NOME_CURSO", columns="SEMESTRE", values="pct_favoravel")
tabela.index.name = "Curso"
st.dataframe((tabela * 100).round(1).astype(str).replace("nan", "—") + "%", width="stretch")
st.caption(f"Cursos com menos de {MIN} respondentes no semestre aparecem com —.")
ui.botao_excel({"Por tipo": por_tipo, "Por curso": por_curso}, "cpa_historico.xlsx", "xls_hist")
ui.nota_sigilo()
