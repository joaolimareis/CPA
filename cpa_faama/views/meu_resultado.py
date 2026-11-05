import streamlit as st

from cpa import auth, charts, metrics, moderacao, ui
from cpa.config import get_settings

ui.aplicar_estilo()
MIN = get_settings().min_respondentes
usuario = auth.usuario_atual()
df, meta = ui.base_do_usuario()  # já vem só com as avaliações deste professor
ui.cabecalho(f"Meu Resultado · {usuario.nome}", "Sua avaliação pelos alunos, comparada à média da instituição", meta)
if df.empty:
    ui.sem_dados()

base = ui.filtros(df, [("NOME_DISCIPLINA", "Disciplina")], "meu")
dados, semestres = ui.filtro_semestre(base, "meu")
ind = metrics.indicadores(dados)

if ind.questionarios < MIN:
    st.warning(f"Você recebeu {ind.questionarios} avaliação(ões) neste recorte. Para proteger o anonimato dos "
               f"alunos, os resultados aparecem a partir de {MIN} respondentes.")
    st.stop()

inst = ui.media_instituicao_docente(semestres)
ui.cartoes([
    ("Avaliações recebidas", ui.num(ind.questionarios), None, None),
    ("% Favorável", ui.pct(ind.pct_favoravel), ui.delta_pp(ind.pct_favoravel, inst and inst.pct_favoravel),
     "A variação compara com a média da instituição."),
    ("Nota global (1 a 5)", ui.num(ind.nota_global, 2), ui.delta_num(ind.nota_global, inst and inst.nota_global), None),
    ("% Indicaria", ui.pct(ind.pct_indicaria), ui.delta_pp(ind.pct_indicaria, inst and inst.pct_indicaria), None),
])
st.caption("As variações nos cartões comparam seu resultado com a média de todos os docentes da instituição.")

c1, c2 = st.columns([3, 2])
with c1:
    st.subheader("Suas respostas por questão")
    st.plotly_chart(charts.barras_distribuicao(metrics.distribuicao(dados, "DESC_QUESTAO", MIN), "DESC_QUESTAO"),
                    width="stretch")
with c2:
    st.subheader("Por disciplina")
    ui.tabela_resumo(metrics.resumo_por(dados, ["NOME_DISCIPLINA"], MIN), {
        "NOME_DISCIPLINA": "Disciplina", "questionarios": "Respondentes",
        "pct_favoravel": "% Favorável", "nota_global": "Nota global"})
    st.caption(f"Disciplinas com menos de {MIN} respondentes aparecem sem resultado.")

st.subheader("Comentários dos alunos")
coment = moderacao.preparar_comentarios(dados, MIN)
coment = coment[coment["VISIVEL"]]
if coment.empty:
    st.info("Nenhum comentário disponível para exibição.")
else:
    for texto in coment["COMENTARIO_EXIBIDO"].sample(frac=1, random_state=7):  # ordem embaralhada
        st.markdown(f"> {texto}")
ui.nota_sigilo()
