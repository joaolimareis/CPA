import streamlit as st

from cpa import charts, metrics, relatorio_docente, ui
from cpa.config import get_settings
from cpa.processing import PROVA_DOCENTE

ui.aplicar_estilo()
MIN = get_settings().min_respondentes
df, meta = ui.base_do_usuario()
df = df[df["TIPO_PROVA"] == PROVA_DOCENTE]
ui.cabecalho("Avaliação Docente e Disciplina", "Como os alunos avaliaram professores e disciplinas", meta)
if df.empty:
    ui.sem_dados()

base = ui.filtros(df, [("NOME_CURSO", "Curso"), ("NOME_PROFESSOR", "Professor"),
                       ("NOME_DISCIPLINA", "Disciplina"), ("STATUS_MATRICULA", "Status da matrícula")], "doc")
dados, semestres = ui.filtro_semestre(base, "doc")
if dados.empty:
    ui.sem_dados()

ind = metrics.indicadores(dados)
ant = ui.indicadores_anteriores(base, semestres)
ui.cartoes([
    ("Avaliações de docentes", ui.num(ind.questionarios), None,
     "Cada professor avaliado por um aluno conta uma avaliação."),
    ("% Favorável", ui.pct(ind.pct_favoravel), ui.delta_pp(ind.pct_favoravel, ant and ant.pct_favoravel), None),
    ("Nota global (1 a 5)", ui.num(ind.nota_global, 2), ui.delta_num(ind.nota_global, ant and ant.nota_global),
     "Média da questão 'atribua uma nota ao desempenho do(a) docente'."),
    ("% Indicaria o docente", ui.pct(ind.pct_indicaria), ui.delta_pp(ind.pct_indicaria, ant and ant.pct_indicaria), None),
    ("Comentários", ui.num(ind.comentarios), None, None),
])

ranking = metrics.resumo_por(dados, ["NOME_PROFESSOR"], MIN)
aba1, aba2, aba3, aba4 = st.tabs(["🏅 Ranking", "📋 Por questão", "🗺️ Mapa de calor", "📚 Professor × disciplina"])

with aba1:
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("% favorável por professor")
        st.plotly_chart(charts.barras_percentual(ranking, "NOME_PROFESSOR", ordenar_por="indice_confianca"),
                        width="stretch")
    with c2:
        st.subheader("Como ler o ranking")
        st.markdown(
            "A ordem usa o **índice de confiança**, e não só o % favorável. Ele desconta a incerteza de "
            "amostras pequenas: um professor com 3 de 3 respostas favoráveis (100%) não passa à frente de "
            "outro com 95 de 100 (95%), porque 3 respostas dizem muito pouco.\n\n"
            f"Professores com menos de **{MIN} respondentes** aparecem na tabela, mas sem resultado.")
        ocultos = int(ranking["protegido"].sum())
        if ocultos:
            st.caption(f"{ocultos} professor(es) oculto(s) por ter(em) menos de {MIN} respondentes.")
    ui.tabela_resumo(ranking.sort_values("indice_confianca", ascending=False, na_position="last"), {
        "NOME_PROFESSOR": "Professor", "questionarios": "Respondentes", "pct_favoravel": "% Favorável",
        "indice_confianca": "Índice de confiança", "nota_global": "Nota global",
        "pct_indicaria": "% Indicaria", "comentarios": "Comentários"})

with aba2:
    st.subheader("Distribuição das respostas por questão")
    st.plotly_chart(charts.barras_distribuicao(metrics.distribuicao(dados, "DESC_QUESTAO"), "DESC_QUESTAO"),
                    width="stretch")

with aba3:
    st.subheader("% favorável: professor × questão")
    st.caption(f"Células vazias têm menos de {MIN} respondentes.")
    escalas = dados[dados["ESCALA"] == "Concordância"]
    st.plotly_chart(charts.mapa_calor(metrics.mapa_calor(escalas, "NOME_PROFESSOR", "DESC_QUESTAO", MIN)),
                    width="stretch")

with aba4:
    detalhe = metrics.resumo_por(dados, ["NOME_PROFESSOR", "NOME_DISCIPLINA"], MIN)
    ui.tabela_resumo(detalhe.sort_values(["NOME_PROFESSOR", "NOME_DISCIPLINA"]), {
        "NOME_PROFESSOR": "Professor", "NOME_DISCIPLINA": "Disciplina", "questionarios": "Respondentes",
        "pct_favoravel": "% Favorável", "nota_global": "Nota global", "pct_indicaria": "% Indicaria"})

st.download_button(
    "📄 Relatório completo da avaliação docente (Excel)",
    data=relatorio_docente.gerar(dados, semestres, MIN),
    file_name=f"Avaliacao_Docente_{'_'.join(s.replace('/', '-') for s in semestres)}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", key="xls_rel_doc",
    help="Resumo por curso, professor × disciplina, por professor e por questão, com os filtros desta página.")
ui.botao_excel({"Ranking": ranking,
                "Professor x disciplina": metrics.resumo_por(dados, ["NOME_PROFESSOR", "NOME_DISCIPLINA"], MIN),
                "Por questão": metrics.resumo_por(dados, ["DESC_QUESTAO"])},
               "cpa_docentes.xlsx", "xls_doc")
ui.nota_sigilo()
