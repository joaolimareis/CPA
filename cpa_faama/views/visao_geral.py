import streamlit as st

from cpa import charts, metrics, ui
from cpa.config import get_settings

MIN = get_settings().min_respondentes

ui.aplicar_estilo()
df, meta = ui.base_do_usuario()
ui.cabecalho("Visão Geral", "Resultado consolidado da avaliação institucional", meta)
if df.empty:
    ui.sem_dados()

base = ui.filtros(df, [("AVALIACAO", "Tipo de avaliação"), ("NOME_CURSO", "Curso"),
                       ("STATUS_MATRICULA", "Status da matrícula")], "vg")
dados, semestres = ui.filtro_semestre(base, "vg")
if dados.empty:
    ui.sem_dados()

ind = metrics.indicadores(dados)
ant = ui.indicadores_anteriores(base, semestres)
ui.cartoes([
    ("Questionários respondidos", ui.num(ind.questionarios), None,
     "Cada professor avaliado conta como um questionário. Não é o número de alunos."),
    ("% Favorável", ui.pct(ind.pct_favoravel), ui.delta_pp(ind.pct_favoravel, ant and ant.pct_favoravel),
     "Concordo totalmente/parcialmente, notas 4 e 5 e 'Sim' sobre as respostas válidas."),
    ("% Neutro", ui.pct(ind.pct_neutro), None, None),
    ("% Desfavorável", ui.pct(ind.pct_desfavoravel), ui.delta_pp(ind.pct_desfavoravel, ant and ant.pct_desfavoravel), None),
    ("Nota média (1 a 5)", ui.num(ind.nota_media, 2), ui.delta_num(ind.nota_media, ant and ant.nota_media), None),
    ("Comentários", ui.num(ind.comentarios), None, None),
])
if ant:
    st.caption("As variações comparam com o semestre anterior.")

por_curso = metrics.resumo_por(dados, ["NOME_CURSO"], MIN)
ocultos = por_curso.loc[por_curso["protegido"], "NOME_CURSO"].tolist()
c1, c2 = st.columns(2)
with c1:
    st.subheader("% favorável por curso")
    st.plotly_chart(charts.barras_percentual(por_curso, "NOME_CURSO"), width="stretch")
with c2:
    st.subheader("Distribuição das respostas por curso")
    st.plotly_chart(charts.barras_distribuicao(metrics.distribuicao(dados, "NOME_CURSO", MIN), "NOME_CURSO"),
                    width="stretch")

if ocultos:
    st.caption(f"Sem resultado por ter menos de {MIN} respondentes: {', '.join(ocultos)}. "
               "Eles continuam somados nos totais do topo da página.")

c3, c4 = st.columns([1, 2])
with c3:
    st.subheader("Distribuição geral")
    st.plotly_chart(charts.rosca(ind), width="stretch")
with c4:
    st.subheader("Evolução por semestre")
    st.plotly_chart(charts.evolucao(metrics.resumo_por(base, ["SEMESTRE", "AVALIACAO"])), width="stretch")

c5, c6 = st.columns([1, 2])
with c5:
    st.subheader("Questionários por curso")
    st.plotly_chart(charts.barras_quantidade(por_curso, "NOME_CURSO"), width="stretch")
with c6:
    st.subheader("Resumo por curso e tipo de avaliação")
    por_curso_tipo = metrics.resumo_por(dados, ["NOME_CURSO", "AVALIACAO"], MIN).sort_values(["NOME_CURSO", "AVALIACAO"])
    ui.tabela_resumo(por_curso_tipo, {
        "NOME_CURSO": "Curso", "AVALIACAO": "Avaliação", "questionarios": "Questionários",
        "pct_favoravel": "% Favorável", "pct_desfavoravel": "% Desfavorável",
        "nota_media": "Nota média", "comentarios": "Comentários"})

ui.botao_excel({"Por curso": por_curso.sort_values("questionarios", ascending=False),
                "Por curso e avaliação": por_curso_tipo}, "cpa_visao_geral.xlsx", "xls_vg")
ui.nota_sigilo()
