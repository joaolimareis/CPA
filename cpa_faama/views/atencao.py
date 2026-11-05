import streamlit as st

from cpa import metrics, ui
from cpa.config import get_settings
from cpa.processing import PROVA_CURSO, PROVA_DOCENTE, PROVA_INFRA

ui.aplicar_estilo()
MIN = get_settings().min_respondentes
df, meta = ui.base_do_usuario()
ui.cabecalho("Pontos de Atenção", "Onde a avaliação indica necessidade de ação", meta)
if df.empty:
    ui.sem_dados()

base = ui.filtros(df, [("NOME_CURSO", "Curso")], "pa")
dados, _ = ui.filtro_semestre(base, "pa")
with st.sidebar:
    limite = st.slider("Alertar a partir de % desfavorável", 5, 50, 15, step=5, format="%d%%") / 100

st.markdown(f"Itens com **{limite:.0%} ou mais de respostas desfavoráveis** e pelo menos {MIN} respondentes, "
            "ordenados pelo **índice de alerta**.")
with st.expander("ℹ️ Como ler esta página"):
    st.markdown(
        "- **% Desfavorável** conta **respostas**: um aluno que responde 10 questões gera 10 respostas. "
        "Por isso, com 1 respondente insatisfeito, o resultado pode chegar a 100%.\n"
        "- **Alunos insatisfeitos** conta **pessoas**: um questionário é insatisfeito quando tem mais respostas "
        "desfavoráveis do que favoráveis. Cada aluno vale um voto.\n"
        "- **Índice de alerta** combina as duas coisas: a proporção de alunos insatisfeitos, descontando a "
        "incerteza de grupos pequenos. 3 insatisfeitos em 5 pesa mais que 1 em 1, porque é um sinal mais firme.")
colunas = {"questionarios": "Respondentes", "avaliacoes_insatisfeitas": "Alunos insatisfeitos",
           "pct_desfavoravel": "% Desfavorável", "indice_alerta": "Índice de alerta"}

docentes = dados[dados["TIPO_PROVA"] == PROVA_DOCENTE]
curso = dados[dados["TIPO_PROVA"] == PROVA_CURSO]
infra = dados[dados["TIPO_PROVA"] == PROVA_INFRA]

c1, c2 = st.columns(2)
with c1:
    st.subheader("👩‍🏫 Professores")
    prof = metrics.pontos_de_atencao(docentes, ["NOME_PROFESSOR"], MIN, limite)
    ui.tabela_resumo(prof, {"NOME_PROFESSOR": "Professor", **colunas})
    st.subheader("📋 Questões da avaliação docente")
    ui.tabela_resumo(metrics.pontos_de_atencao(docentes, ["DESC_QUESTAO"], MIN, limite),
                     {"DESC_QUESTAO": "Questão", **colunas})
with c2:
    st.subheader("🎓 Avaliação do curso")
    ui.tabela_resumo(metrics.pontos_de_atencao(curso, ["NOME_CURSO", "DESC_QUESTAO"], MIN, limite),
                     {"NOME_CURSO": "Curso", "DESC_QUESTAO": "Questão", **colunas})
    st.subheader("🏫 Infraestrutura (instituição toda)")
    ui.tabela_resumo(metrics.pontos_de_atencao(infra, ["DESC_QUESTAO"], MIN, limite),
                     {"DESC_QUESTAO": "Questão", **colunas})
    st.subheader("📚 Professor × disciplina")
    ui.tabela_resumo(metrics.pontos_de_atencao(docentes, ["NOME_PROFESSOR", "NOME_DISCIPLINA"], MIN, limite),
                     {"NOME_PROFESSOR": "Professor", "NOME_DISCIPLINA": "Disciplina", **colunas})

ui.nota_sigilo()
