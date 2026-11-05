import streamlit as st

from cpa import relatorio_pdf, repository, ui
from cpa.config import get_settings

ui.aplicar_estilo()
s = get_settings()
df, meta = ui.base_do_usuario()
ui.cabecalho("Relatório da CPA", "Documento em PDF com os resultados consolidados do semestre, pronto para "
             "apresentar à direção e a avaliadores externos", meta)
if df.empty:
    ui.sem_dados()

semestres = sorted(df["SEMESTRE"].dropna().unique(), reverse=True)
semestre = st.selectbox("Semestre", semestres)
st.markdown(
    "O relatório traz: metodologia, participação por curso, resultado geral por avaliação, avaliação docente por "
    "curso e por questão, avaliação de cada curso, infraestrutura e pontos de atenção. **Não traz nomes de alunos "
    "nem de professores**, e grupos com poucos respondentes não são detalhados.")

if st.button("Gerar relatório em PDF", type="primary"):
    part = None
    if repository.participacao_configurada():
        p, _ = ui.participacao_do_usuario()
        part = p[p["SEMESTRE"] == semestre]
    with st.spinner("Montando o relatório…"):
        pdf = relatorio_pdf.gerar(df[df["SEMESTRE"] == semestre], part, semestre, s.min_respondentes,
                                  s.nome_instituicao)
    st.download_button("Baixar relatório", data=pdf, file_name=f"Relatorio_CPA_{semestre.replace('/', '-')}.pdf",
                       mime="application/pdf", type="primary")
    st.success("Relatório gerado. Clique em Baixar relatório.")
ui.nota_sigilo()
