import plotly.graph_objects as go
import streamlit as st

from cpa import auth, charts, participacao, repository, ui, validacao
from cpa.processing import PROVA_DOCENTE

ui.aplicar_estilo()
usuario = auth.usuario_atual()
if not usuario or usuario.perfil != "admin":
    st.error("Acesso restrito à CPA.")
    st.stop()

df, meta = ui.carregar()
ui.cabecalho("Validação dos Dados", "O que entrou nos resultados, o que foi descartado e por quê, por curso e professor", meta)

validas_todas = df[df["TIPO_PROVA"] == PROVA_DOCENTE]
descartes_todos = ui.descartes()
if "SEMESTRE_DISCIPLINA" not in df.columns:
    st.warning("A consulta da CPA ainda não informa o semestre da disciplina. Atualize a FAAMACPA.6 com o arquivo "
               "`sql/consulta_cpa_v10.sql` para esta página mostrar as avaliações de professores de semestres anteriores.")

st.markdown(
    "<div class='nota-sigilo'><b>Regra:</b> uma avaliação docente só entra nos resultados e no ranking se "
    "<b>(1)</b> o professor dá aula numa disciplina <b>do semestre da avaliação</b> e "
    "<b>(2)</b> é a avaliação <b>mais recente</b> do aluno para aquele professor e disciplina. "
    "As demais são descartadas e aparecem aqui, separadas por motivo.</div>", unsafe_allow_html=True)
st.write("")

# filtros (semestre e curso valem para as avaliações aceitas e para as descartadas)
dados, semestres = ui.filtro_semestre(validas_todas, "val")
cursos_opc = sorted(set(validas_todas["NOME_CURSO"].dropna()) |
                    (set(descartes_todos["NOME_CURSO"].dropna()) if not descartes_todos.empty else set()))
with st.sidebar:
    cursos = st.multiselect("Curso", cursos_opc, placeholder="Todos", key="val_curso")
desc = descartes_todos
if not desc.empty:
    desc = desc[desc["SEMESTRE"].isin(semestres)]
if cursos:
    dados = dados[dados["NOME_CURSO"].isin(cursos)]
    desc = desc[desc["NOME_CURSO"].isin(cursos)] if not desc.empty else desc

geral = validacao.resumo(dados.assign(_t="Total"), desc.assign(_t="Total") if not desc.empty else desc, ["_t"])
g = geral.iloc[0] if not geral.empty else None
st.subheader("1. Visão geral das avaliações docentes")
ui.cartoes([
    ("Avaliações recebidas", ui.num(g["recebidas"] if g is not None else 0), None,
     "Tudo o que os alunos responderam na avaliação docente do semestre."),
    ("Aceitas", ui.num(g["validas"] if g is not None else 0), None, "Entram nos resultados e no ranking."),
    ("Descartadas: professor de semestre anterior", ui.num(g["semestre_anterior"] if g is not None else 0), None,
     "O aluno avaliou um professor de disciplina de outro semestre."),
    ("Descartadas: repetidas", ui.num(g["repetidas"] if g is not None else 0), None,
     "O aluno avaliou o mesmo professor e disciplina mais de uma vez; vale só a mais recente."),
    ("% aceitas", ui.pct(g["pct_validas"] if g is not None else None), None, None),
])
st.caption("Os números contam questionários (cada professor avaliado por um aluno é um questionário).")

# 2. por curso
st.subheader("2. Por curso")
por_curso = validacao.resumo(dados, desc, ["NOME_CURSO"])
c1, c2 = st.columns([3, 2])
with c1:
    if por_curso.empty:
        st.info("Sem avaliações para os filtros selecionados.")
    else:
        ordem = por_curso.sort_values("recebidas")
        fig = go.Figure()
        for coluna, rotulo, cor in (("validas", "Aceitas", "#2E7D32"),
                                    ("semestre_anterior", "Professor de semestre anterior", "#C62828"),
                                    ("repetidas", "Repetidas", "#F18F01")):
            fig.add_bar(y=ordem["NOME_CURSO"], x=ordem[coluna], name=rotulo, orientation="h", marker_color=cor,
                        hovertemplate="%{y}: %{x} avaliações<extra>" + rotulo + "</extra>")
        fig.update_layout(barmode="stack", height=max(280, 50 * len(ordem) + 80), template="plotly_white",
                          legend=dict(orientation="h", y=1.1, x=0, title=None), margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, width="stretch")
with c2:
    ui.tabela_resumo(por_curso, {"NOME_CURSO": "Curso", "recebidas": "Recebidas", "validas": "Aceitas",
                                 "semestre_anterior": "Semestre anterior", "repetidas": "Repetidas",
                                 "pct_validas": "% aceitas"})

# 3. por professor
st.subheader("3. Por professor")
por_prof = validacao.resumo(dados, desc, ["NOME_PROFESSOR"])
ui.tabela_resumo(por_prof, {"NOME_PROFESSOR": "Professor", "recebidas": "Recebidas", "validas": "Aceitas",
                            "semestre_anterior": "Semestre anterior", "repetidas": "Repetidas",
                            "pct_validas": "% aceitas"}, altura=380)
professores = por_prof["NOME_PROFESSOR"].dropna().tolist()
if professores:
    escolhido = st.selectbox("Ver o detalhe de um professor", professores, index=None, placeholder="Escolha um professor")
    if escolhido:
        det = validacao.detalhe_professor(dados, desc, escolhido)
        st.markdown(f"**{escolhido}**: avaliações por disciplina e semestre da disciplina")
        st.dataframe(det.rename(columns={"NOME_DISCIPLINA": "Disciplina", "NOME_CURSO": "Curso do aluno",
                                         "SEMESTRE_DISCIPLINA": "Semestre da disciplina", "SITUACAO": "Situação",
                                         "avaliacoes": "Avaliações"}), hide_index=True, width="stretch")

# 4. professores de semestres anteriores
st.subheader("4. Professores de semestres anteriores que os alunos avaliaram")
c3, c4 = st.columns([3, 2])
with c3:
    st.markdown("**Por disciplina e semestre da disciplina**")
    antigos = validacao.professores_anteriores(desc)
    st.dataframe(antigos.rename(columns={"NOME_PROFESSOR": "Professor", "NOME_DISCIPLINA": "Disciplina",
                                         "SEMESTRE_DISCIPLINA": "Semestre da disciplina", "avaliacoes": "Avaliações"}),
                 hide_index=True, width="stretch", height=380)
with c4:
    st.markdown("**Professores sem disciplina neste semestre**")
    st.caption("Receberam avaliações, mas nenhuma de disciplina do semestre selecionado "
               "(por exemplo, professores que já saíram).")
    fora = validacao.professores_fora_do_semestre(dados, desc)
    st.dataframe(fora.rename(columns={"NOME_PROFESSOR": "Professor", "avaliacoes_descartadas": "Avaliações descartadas",
                                      "ultimo_semestre_avaliado": "Semestre mais recente avaliado"}),
                 hide_index=True, width="stretch", height=380)

# 5. participação
st.subheader("5. Participação por curso (o que vale para o ranking)")
if not repository.participacao_configurada():
    st.info("Configure a consulta de participação para ver esta seção.")
else:
    part, _ = ui.participacao_do_usuario()
    part = part[part["SEMESTRE"].isin(semestres)]
    part = part[part["DOCENTE_ESPERADAS"] > 0]
    if cursos:
        part = part[part["NOME_CURSO"].isin(cursos)]
    st.caption("Na consulta de participação, só conta como participante quem respondeu a avaliação do curso, da "
               "infraestrutura ou de um professor de disciplina que cursa no semestre. Quem avaliou só professores "
               "antigos não conta.")
    rk = participacao.ranking(part, ["NOME_CURSO"], ordenar="taxa_adesao")
    ui.tabela_resumo(rk, {"posicao": "#", "NOME_CURSO": "Curso", "ALUNOS_MATRICULADOS": "Matriculados",
                          "ALUNOS_RESPONDERAM": "Responderam", "taxa_adesao": "% Adesão", "indice": "Índice",
                          "DOCENTE_ESPERADAS": "Aval. docentes esperadas", "DOCENTE_RESPONDIDAS": "Aval. docentes válidas",
                          "completude": "% Completude docente"})

ui.botao_excel({"Por curso": por_curso, "Por professor": por_prof,
                "Professores anteriores": validacao.professores_anteriores(desc)},
               "cpa_validacao.xlsx", "xls_val")
