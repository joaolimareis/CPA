import plotly.express as px
import streamlit as st

from cpa import auditoria, auth, charts, ui

ui.aplicar_estilo()
usuario = auth.usuario_atual()
if not usuario or usuario.perfil != "admin":
    st.error("Acesso restrito à CPA.")
    st.stop()

df, meta = ui.carregar()
ui.cabecalho("Auditoria dos Dados", "Conferência da base com o TOTVS: totais, consistência e linha do tempo", meta)
st.markdown("Use esta página junto com o arquivo **`sql/auditoria_totvs.sql`**: cada bloco abaixo indica qual "
            "consulta rodar no RM para comparar os números.")

# 1. Funil
st.subheader("1. Caminho dos dados: da API até as telas")
rel = meta.get("relatorio", {})
c = st.columns(7)
c[0].metric("Linhas recebidas da API", ui.num(rel.get("linhas_api", meta.get("linhas_api"))),
            help="Compare com o total de registros ao executar a consulta FAAMACPA.6 dentro do RM.")
c[1].metric("Removidas: cursos fora da CPA", ui.num(rel.get("removidas_cursos_excluidos")))
c[2].metric("Removidas: textos informativos", ui.num(rel.get("removidas_textos_informativos")),
            help="Apresentação e agradecimento da CPA (resposta ENTENDI).")
c[3].metric("Removidas: professor de semestre anterior", ui.num(rel.get("removidas_semestre_anterior")),
            help="Aluno avaliou professor de disciplina de outro semestre. Detalhes na página Validação.")
c[4].metric("Removidas: avaliações repetidas", ui.num(rel.get("removidas_avaliacoes_repetidas")),
            help="Aluno que avaliou o mesmo professor/disciplina mais de uma vez: vale só a mais recente.")
c[5].metric("Removidas: questões anuladas", ui.num(rel.get("removidas_questoes_anuladas")),
            help="Questões aplicadas por engano numa prova (ex.: questões do Direito na prova da Psicologia).")
c[6].metric("Linhas usadas nas análises", ui.num(rel.get("linhas_finais", len(df))))

# 2. Reconciliação
st.subheader("2. Totais por prova e período")
st.caption("Compare a coluna **Questionários** com a consulta 2 do arquivo SQL (coluna QUESTIONARIOS). "
           "Diferenças esperadas: cursos excluídos, matrículas que não casam com o semestre e filtros de pensionato/etapa.")
st.dataframe(auditoria.reconciliacao_por_prova(df).rename(columns={
    "CODPROVA": "Cód. prova", "NOME_PROVA": "Prova", "AVALIACAO": "Tipo", "PERIODO_PROVA": "Período",
    "questionarios": "Questionários", "linhas": "Linhas", "respostas_validas": "Respostas válidas",
    "comentarios": "Comentários", "cursos": "Cursos dos alunos"}), hide_index=True, width="stretch")

# 3. Checagens
st.subheader("3. Checagens automáticas de consistência")
for chk in auditoria.checagens(df):
    if chk.ok:
        icone = "✅"
    else:
        icone = "⚠️" if chk.gravidade == "aviso" else "❌"
    with st.expander(f"{icone} {chk.nome}: {ui.num(chk.problemas)}", expanded=not chk.ok and chk.gravidade == "erro"):
        st.write(chk.explicacao)
        if not chk.ok:
            st.dataframe(chk.detalhe, hide_index=True, width="stretch")

# 4. Linha do tempo
st.subheader("4. Quando as respostas foram dadas")
tempo = auditoria.linha_do_tempo(df)
if tempo is None:
    st.info("A consulta SQL ainda não traz a data/hora das respostas. Rode as consultas 1 e 5 do arquivo "
            "`sql/auditoria_totvs.sql` para descobrir o campo de data e veja a consulta 10 para incluir a coluna "
            "**DATA_RESPOSTA** na consulta da CPA. Assim que ela existir, esta seção aparece sozinha.")
else:
    t1, t2 = st.columns([2, 1])
    with t1:
        fig = px.bar(tempo["por_dia"], x="DIA", y="questionarios", color="AVALIACAO",
                     color_discrete_sequence=[charts.AZUL, "#F18F01", "#2E86AB"])
        fig.update_layout(height=320, template="plotly_white", legend_title=None, xaxis_title=None,
                          yaxis_title="Questionários iniciados")
        st.plotly_chart(fig, width="stretch")
    with t2:
        fig = px.bar(tempo["por_hora"], x="HORA", y="questionarios", color_discrete_sequence=["#2E86AB"])
        fig.update_layout(height=320, template="plotly_white", xaxis_title="Hora do dia", yaxis_title=None)
        st.plotly_chart(fig, width="stretch")
    st.dataframe(tempo["por_prova"].rename(columns={"NOME_PROVA": "Prova", "primeira": "Primeira resposta",
                                                     "ultima": "Última resposta"}), hide_index=True, width="stretch")

# 5. Investigação por curso
st.subheader("5. Investigação por curso")
cursos = sorted(df["NOME_CURSO"].dropna().unique())
padrao = cursos.index("Teologia") if "Teologia" in cursos else 0
curso = st.selectbox("Curso", cursos, index=padrao)
st.caption("Para o mesmo curso, compare com as consultas 6 (participação) e 7 (taxa de resposta por turma) do arquivo SQL.")
for titulo, tabela in auditoria.investigar_curso(df, curso).items():
    st.markdown(f"**{titulo}**")
    st.dataframe(tabela, hide_index=True, width="stretch")

# 6. Consulta de um questionário
st.subheader("6. Conferir um questionário específico")
st.caption("O ID é o BH.ID do TOTVS (tabela BHISTORICO). Busque o mesmo ID no RM e compare resposta por resposta.")
id_busca = st.text_input("ID do questionário (ID_RESPONDENTE)")
if id_busca:
    linhas = df[df["ID_RESPONDENTE"] == id_busca.strip()]
    if linhas.empty:
        st.warning("Questionário não encontrado na base tratada (pode ter sido filtrado pela consulta SQL).")
    else:
        st.dataframe(linhas[["NOME_PROVA", "PERIODO_PROVA", "NOME_CURSO", "NOME_PROFESSOR", "NOME_DISCIPLINA",
                             "CODMATERIA", "CODQUESTAO", "DESC_QUESTAO", "CODRESPOSTA", "ALTERNATIVA", "GRUPO",
                             "COMENTARIO"]], hide_index=True, width="stretch")
