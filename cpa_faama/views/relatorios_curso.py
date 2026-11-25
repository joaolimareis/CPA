import io
import zipfile

import streamlit as st

from cpa import auth, moderacao, relatorio_coordenador, repository, ui
from cpa.config import get_settings

ui.aplicar_estilo()
s = get_settings()
usuario = auth.usuario_atual()
df, meta = ui.base_do_usuario()
ui.cabecalho("Relatórios por curso", "Excel para cada coordenação: todas as dimensões de cada professor e disciplina, "
             "avaliação do curso, infraestrutura, comentários e participação por turma", meta)
if df.empty:
    ui.sem_dados()

semestres = sorted(df["SEMESTRE"].dropna().unique(), reverse=True)
c1, c2 = st.columns(2)
semestre = c1.selectbox("Semestre", semestres)
base_sem = df[df["SEMESTRE"] == semestre]
cursos = sorted(base_sem["NOME_CURSO"].dropna().unique())
curso = c2.selectbox("Curso", cursos)

part_sem = None
if repository.participacao_configurada():
    p, _ = ui.participacao_do_usuario()
    part_sem = p[p["SEMESTRE"] == semestre]

st.markdown(
    "Cada planilha traz: **Resumo** do curso, **Docentes (dimensões)** com o % favorável de cada questão por "
    "professor e disciplina, **Docentes por questão**, **Comentários docentes**, **Avaliação do curso**, "
    "**Infraestrutura**, **Comentários do curso** e **Participação por turma**. Professores com menos de "
    f"{s.min_respondentes} respondentes aparecem sem resultado, e só entram comentários aprovados na moderação.")


def gerar(c: str) -> bytes:
    dados = base_sem[base_sem["NOME_CURSO"] == c]
    comentarios = moderacao.preparar_comentarios(dados, s.min_respondentes)
    part = part_sem[part_sem["NOME_CURSO"] == c] if part_sem is not None else None
    return relatorio_coordenador.gerar(dados, comentarios, part, c, semestre, s.min_respondentes)


def nome_arquivo(c: str) -> str:
    return f"CPA_{c.replace(' ', '_')}_{semestre.replace('/', '-')}.xlsx"


b1, b2 = st.columns(2)
if b1.button(f"Gerar relatório de {curso}", type="primary", width="stretch"):
    with st.spinner("Montando a planilha…"):
        st.session_state["rel_curso"] = (nome_arquivo(curso), gerar(curso))
if "rel_curso" in st.session_state:
    nome, conteudo = st.session_state["rel_curso"]
    b1.download_button(f"⬇️ Baixar {nome}", conteudo, file_name=nome, width="stretch",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if usuario and usuario.perfil == "admin" and len(cursos) > 1:
    if b2.button("Gerar de todos os cursos (ZIP)", width="stretch"):
        with st.spinner("Montando uma planilha por curso…"):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
                for c in cursos:
                    z.writestr(nome_arquivo(c), gerar(c))
            st.session_state["rel_todos"] = buffer.getvalue()
    if "rel_todos" in st.session_state:
        b2.download_button("⬇️ Baixar ZIP com todos os cursos", st.session_state["rel_todos"],
                           file_name=f"CPA_relatorios_por_curso_{semestre.replace('/', '-')}.zip",
                           mime="application/zip", width="stretch")

st.markdown("<div class='nota-sigilo'>Os relatórios trazem nomes de professores e comentários dos alunos. "
            "Envie cada planilha somente à coordenação do próprio curso.</div>", unsafe_allow_html=True)
