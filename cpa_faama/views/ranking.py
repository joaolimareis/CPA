import plotly.express as px
import streamlit as st

from cpa import auth, charts, participacao, relatorio_participacao, repository, ui

ui.aplicar_estilo()

if not repository.participacao_configurada():
    ui.cabecalho("Participação", "Quem mais participou da avaliação", None)
    st.info("Configure a consulta de participação: cadastre no RM a consulta do arquivo "
            "`sql/participacao.sql` e informe o código em `TOTVS_CONSULTA_PARTICIPACAO` no `.env`.")
    st.stop()

df, meta = ui.participacao_do_usuario()
ui.cabecalho("Participação", "Quem mais participou da avaliação, de forma proporcional ao tamanho de cada curso e turma",
             meta)
if df.empty:
    ui.sem_dados()

semestres = sorted(df["SEMESTRE"].dropna().unique())
tot = df.groupby("SEMESTRE")[["ALUNOS_RESPONDERAM", "ALUNOS_MATRICULADOS"]].sum()
adesao_sem = tot["ALUNOS_RESPONDERAM"] / tot["ALUNOS_MATRICULADOS"]
# Abre no semestre mais recente que já tenha avaliação de fato (10% de adesão); senão, no de maior adesão
com_avaliacao = [s for s in semestres if adesao_sem.get(s, 0) >= 0.10]
padrao = max(com_avaliacao) if com_avaliacao else adesao_sem.idxmax()
with st.sidebar:
    st.markdown("#### Filtros")
    semestre = st.selectbox("Semestre", semestres, index=semestres.index(padrao))
    cursos = st.multiselect("Curso", sorted(df["NOME_CURSO"].dropna().unique()), placeholder="Todos")
    meta_adesao = st.slider("Meta de adesão", 10, 100, 60, step=5, format="%d%%") / 100
    min_alunos = st.number_input("Ranking por turma: ignorar turmas com menos de (alunos)", 0, 50, 5,
                                 help="Vale só para o ranking por turma. Os totais e o ranking por curso usam todos os "
                                      "alunos ativos, como na contagem oficial de alunos por curso.")
    sem_avaliacao = st.checkbox("Ranking por turma: ignorar turmas sem avaliação docente aberta", value=True,
                                help="Turmas em que nenhuma disciplina tinha avaliação disponível (0 avaliações "
                                     "esperadas) não tiveram como participar e não devem ser penalizadas.")

# Cursos e totais: todos os alunos ativos (bate com a contagem oficial de alunos por curso).
# Turmas: ignora turmas residuais e sem avaliação aberta, para a comparação entre turmas ser justa.
todos = df[df["SEMESTRE"] == semestre]
if cursos:
    todos = todos[todos["NOME_CURSO"].isin(cursos)]
dados = todos[todos["ALUNOS_MATRICULADOS"] >= min_alunos]
if sem_avaliacao:
    dados = dados[dados["DOCENTE_ESPERADAS"] > 0]
if todos.empty:
    ui.sem_dados()

geral = participacao.ranking(todos.assign(_t="Total"), ["_t"]).iloc[0]
por_curso = participacao.ranking(todos, ["NOME_CURSO"], ordenar="taxa_adesao")
por_turma = participacao.ranking(dados, ["NOME_CURSO", "CODTURMA", "NOME_TURMA"])
abaixo = por_turma[por_turma["taxa_adesao"] < meta_adesao]

ui.cartoes([
    ("Taxa de adesão", ui.pct(geral["taxa_adesao"]), None, "Alunos que responderam ÷ alunos matriculados."),
    ("Alunos que responderam", f"{ui.num(geral['ALUNOS_RESPONDERAM'])} de {ui.num(geral['ALUNOS_MATRICULADOS'])}", None, None),
    ("Completude docente", ui.pct(geral["completude"]), None,
     "Avaliações docentes respondidas ÷ avaliações que os alunos poderiam ter respondido."),
    ("Turmas abaixo da meta", f"{len(abaixo)} de {len(por_turma)}", None, f"Meta de {meta_adesao:.0%} de adesão."),
])

with st.expander("ℹ️ Como o ranking é calculado"):
    st.markdown(
        "- **Taxa de adesão** = alunos que responderam pelo menos um questionário ÷ alunos matriculados.\n"
        "- **Ranking por curso**: ordenado pela taxa de adesão.\n"
        "- **Ranking por turma**: ordenado pelo **índice**, a taxa ajustada pelo tamanho da turma (limite inferior "
        "de Wilson). Como as turmas variam muito de tamanho, uma turma de 3 alunos com 3 respostas (100%) fica com "
        "índice 44%, enquanto uma de 50 com 45 respostas (90%) fica com 79%. Assim, nem as turmas grandes ganham "
        "por volume, nem as pequenas por acaso.\n"
        "- **Completude docente** = avaliações de professores respondidas ÷ avaliações possíveis (soma das "
        "disciplinas de cada aluno). Equilibra cursos com mais ou menos disciplinas.")

inconsistentes = por_turma[por_turma["inconsistente"]]
if len(inconsistentes):
    st.warning(f"{len(inconsistentes)} turma(s) com mais avaliações docentes respondidas do que esperadas. "
               "A completude delas não é exibida: revise a consulta de participação (ver sql/participacao.sql).")

st.subheader("Termômetro de participação dos cursos")
st.caption("Verde: atingiu a meta. Amarelo: passou da metade da meta. Vermelho: abaixo da metade.")
st.plotly_chart(charts.termometro(por_curso, "NOME_CURSO", meta_adesao, vertical=True), width="stretch")

# ---------- por turma, para enviar aos coordenadores ----------
st.subheader("Participação por turma")
st.caption("Escolha o curso para ver o termômetro das turmas e baixar o documento para enviar à coordenação.")
cursos_turma = sorted(dados["NOME_CURSO"].dropna().unique())
usuario = auth.usuario_atual()
if cursos_turma:
    ct1, ct2 = st.columns([2, 3])
    curso_turma = ct1.selectbox("Curso", cursos_turma, key="curso_turma")
    turmas_curso = participacao.ranking(dados[dados["NOME_CURSO"] == curso_turma], ["NOME_TURMA"])
    tot_curso = participacao.ranking(todos[todos["NOME_CURSO"] == curso_turma].assign(_t="T"), ["_t"]).iloc[0]
    ct2.metric(f"Adesão em {curso_turma}", ui.pct(tot_curso["taxa_adesao"]),
               help=f"{ui.num(tot_curso['ALUNOS_RESPONDERAM'])} de {ui.num(tot_curso['ALUNOS_MATRICULADOS'])} alunos.")
    st.plotly_chart(charts.termometro(turmas_curso, "NOME_TURMA", meta_adesao, vertical=False), width="stretch")
    tabela_turma = turmas_curso.assign(faltam=relatorio_participacao.faltam_para_meta(turmas_curso, meta_adesao))
    tabela_turma = tabela_turma.sort_values("taxa_adesao", ascending=False)
    exibir = tabela_turma[["NOME_TURMA", "ALUNOS_MATRICULADOS", "ALUNOS_RESPONDERAM", "taxa_adesao", "faltam"]].copy()
    exibir["taxa_adesao"] = exibir["taxa_adesao"] * 100
    st.dataframe(exibir.rename(columns={"NOME_TURMA": "Turma", "ALUNOS_MATRICULADOS": "Alunos ativos",
                                        "ALUNOS_RESPONDERAM": "Responderam", "taxa_adesao": "% Adesão",
                                        "faltam": "Faltam p/ meta"}),
                 hide_index=True, width="stretch",
                 column_config={"% Adesão": st.column_config.ProgressColumn("% Adesão", format="%.1f%%",
                                                                            min_value=0, max_value=100)})
    b1, b2, b3 = st.columns(3)
    b1.download_button(
        f"📄 PDF de {curso_turma}", key="pdf_turma_curso", type="primary", width="stretch",
        data=relatorio_participacao.gerar(dados, todos, semestre, [curso_turma], meta_adesao),
        file_name=f"Participacao_{curso_turma.replace(' ', '_')}_{semestre.replace('/', '-')}.pdf",
        mime="application/pdf")
    if usuario and usuario.perfil == "admin" and len(cursos_turma) > 1:
        b2.download_button(
            "📄 PDF de todos os cursos", key="pdf_turma_todos", width="stretch",
            data=relatorio_participacao.gerar(dados, todos, semestre, cursos_turma, meta_adesao),
            file_name=f"Participacao_por_turma_{semestre.replace('/', '-')}.pdf", mime="application/pdf",
            help="Primeira página com o termômetro dos cursos e depois uma página por curso, com as turmas.")
    from cpa.export import para_excel
    b3.download_button("⬇️ Excel das turmas", key="xls_turma_curso", width="stretch",
                       data=para_excel({curso_turma[:31]: tabela_turma.drop(columns=["inconsistente"])}),
                       file_name=f"Turmas_{curso_turma.replace(' ', '_')}_{semestre.replace('/', '-')}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("Nenhuma turma com avaliação aberta para os filtros escolhidos.")

st.subheader("Ranking por curso")
grafico = por_curso.rename(columns={"ALUNOS_MATRICULADOS": "questionarios"})
st.plotly_chart(charts.barras_percentual(grafico, "NOME_CURSO", "taxa_adesao", altura=280),
                width="stretch")
ui.tabela_resumo(por_curso, {"posicao": "#", "NOME_CURSO": "Curso", "ALUNOS_MATRICULADOS": "Matriculados",
                             "ALUNOS_RESPONDERAM": "Responderam", "taxa_adesao": "% Adesão",
                             "indice": "Índice", "taxa_docente": "% Docente",
                             "taxa_institucional": "% Institucional", "completude": "% Completude docente"})

st.subheader("Ranking por turma")
ui.tabela_resumo(por_turma, {"posicao": "#", "NOME_CURSO": "Curso", "NOME_TURMA": "Turma",
                             "ALUNOS_MATRICULADOS": "Matriculados", "ALUNOS_RESPONDERAM": "Responderam",
                             "taxa_adesao": "% Adesão", "indice": "Índice", "taxa_docente": "% Docente",
                             "taxa_institucional": "% Institucional", "completude": "% Completude docente"},
                 altura=520)

c3, c4 = st.columns([3, 2])
with c3:
    st.subheader("Tamanho da turma × adesão")
    st.caption("Cada ponto é uma turma. Mostra se a adesão depende do tamanho da turma.")
    fig = px.scatter(por_turma, x="ALUNOS_MATRICULADOS", y="taxa_adesao", color="NOME_CURSO",
                     hover_data={"NOME_TURMA": True, "ALUNOS_RESPONDERAM": True}, size="ALUNOS_MATRICULADOS",
                     size_max=28, labels={"ALUNOS_MATRICULADOS": "Alunos matriculados", "taxa_adesao": "Adesão",
                                          "NOME_CURSO": "Curso"})
    fig.add_hline(y=meta_adesao, line_dash="dash", line_color="#C62828", annotation_text="meta")
    fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
    fig.update_layout(height=380, template="plotly_white", legend_title=None)
    st.plotly_chart(fig, width="stretch")
with c4:
    st.subheader("⚠️ Turmas abaixo da meta")
    if abaixo.empty:
        st.success("Todas as turmas atingiram a meta.")
    else:
        faltam = (abaixo["ALUNOS_MATRICULADOS"] * meta_adesao).apply(lambda v: int(-(-v // 1))) - abaixo["ALUNOS_RESPONDERAM"]
        alerta = abaixo.assign(faltam=faltam.clip(lower=0)).sort_values("taxa_adesao")
        st.dataframe(alerta[["NOME_TURMA", "ALUNOS_RESPONDERAM", "ALUNOS_MATRICULADOS", "faltam"]].rename(columns={
            "NOME_TURMA": "Turma", "ALUNOS_RESPONDERAM": "Responderam", "ALUNOS_MATRICULADOS": "Matriculados",
            "faltam": "Faltam p/ meta"}), hide_index=True, width="stretch", height=340)

ui.botao_excel({"Por curso": por_curso.drop(columns=["inconsistente"]),
                "Por turma": por_turma.drop(columns=["inconsistente"])}, f"cpa_participacao_{semestre.replace('/', '-')}.xlsx",
               "xls_rank")
