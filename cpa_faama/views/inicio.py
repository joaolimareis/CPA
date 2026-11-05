from datetime import date

import streamlit as st

from cpa import auth, metrics, participacao, repository, ui
from cpa.config import get_settings
from cpa.navegacao import PAGINAS, chaves_do_perfil

ui.aplicar_estilo()
s = get_settings()
usuario = auth.usuario_atual()
df, meta = ui.base_do_usuario()
ui.cabecalho("Avaliação Institucional", f"Comissão Própria de Avaliação da {s.nome_instituicao}: "
             "o que os alunos dizem sobre professores, cursos e infraestrutura", meta)
if df.empty:
    ui.sem_dados()

semestres = sorted(df["SEMESTRE"].dropna().unique())
atual = semestres[-1]
dados = df[df["SEMESTRE"] == atual]

# ---------- situação da avaliação do semestre mais recente ----------
part = None
if repository.participacao_configurada():
    p, _ = ui.participacao_do_usuario()
    p = p[p["SEMESTRE"] == atual]
    if not p.empty:
        part = participacao.ranking(p.assign(_t="Total"), ["_t"]).iloc[0]

dias = None
if s.prazo_avaliacao:
    try:
        dias = (date.fromisoformat(s.prazo_avaliacao) - date.today()).days
    except ValueError:
        dias = None

c1, c2 = st.columns([5, 7], gap="large")
with c1:
    if part is not None:
        adesao = float(part["taxa_adesao"] or 0)
        prazo = ""
        if dias is not None:
            prazo = (f" A avaliação fecha em {dias} dia(s)." if dias > 0 else
                     " A avaliação fecha hoje." if dias == 0 else " A avaliação já foi encerrada.")
        st.markdown(
            f"<div class='status-avaliacao'><div class='rotulo'>Participação em {atual}</div>"
            f"<div class='numero'>{ui.pct(adesao)}</div>"
            f"<div class='rotulo'>{ui.num(part['ALUNOS_RESPONDERAM'])} de {ui.num(part['ALUNOS_MATRICULADOS'])} "
            f"alunos responderam.{prazo}</div>"
            f"<div class='barra'><span style='width:{min(adesao, 1) * 100:.1f}%'></span></div></div>",
            unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='status-avaliacao'><div class='rotulo'>Semestre mais recente</div>"
                    f"<div class='numero'>{atual}</div></div>", unsafe_allow_html=True)
with c2:
    ind = metrics.indicadores(dados)
    a, b = st.columns(2)
    a.metric("Questionários respondidos", ui.num(ind.questionarios),
             help="Cada professor avaliado conta como um questionário.")
    b.metric("Respostas favoráveis", ui.pct(ind.pct_favoravel))
    a.metric("Nota média (1 a 5)", ui.num(ind.nota_media, 2))
    b.metric("Nota global dos docentes", ui.num(ind.nota_global, 2))

# ---------- resultado por avaliação ----------
st.subheader(f"Resultado por avaliação em {atual}")
por_tipo = metrics.resumo_por(dados, ["AVALIACAO"])
colunas = st.columns(max(len(por_tipo), 1))
for coluna, (_, linha) in zip(colunas, por_tipo.sort_values("AVALIACAO", ascending=False).iterrows()):
    coluna.metric(linha["AVALIACAO"], ui.pct(linha["pct_favoravel"]),
                  help=f"{ui.num(linha['questionarios'])} questionários; respostas favoráveis sobre as válidas.")
if len(semestres) > 1:
    st.caption(f"Semestres disponíveis: {', '.join(semestres)}. Veja a evolução na página Histórico.")

# ---------- atalhos ----------
st.subheader("Onde encontrar cada informação")
DESCRICOES = {
    "visao": "Resultado consolidado por curso e tipo de avaliação.",
    "docentes": "Professores e disciplinas, com relatório em Excel.",
    "curso": "Coordenação, estágios e práticas de cada curso.",
    "infra": "Salas, biblioteca, Wi-Fi, alimentação e atendimento.",
    "comentarios": "O que os alunos escreveram, já moderado.",
    "atencao": "Itens com mais respostas desfavoráveis.",
    "ranking": "Adesão proporcional por curso e turma.",
    "historico": "Evolução da participação e dos resultados.",
    "relatorio": "Relatório da CPA em PDF para apresentação.",
    "metodologia": "Como os dados são coletados e tratados.",
}
disponiveis = [c for c in chaves_do_perfil(usuario.perfil) if c in DESCRICOES]
grade = st.columns(3)
for i, chave in enumerate(disponiveis):
    caminho, titulo, icone = PAGINAS[chave]
    with grade[i % 3]:
        try:
            st.page_link(caminho, label=titulo, icon=icone)
        except Exception:  # noqa: BLE001 - fora do menu (ex.: testes), mostra só o nome
            st.markdown(f"{icone} **{titulo}**")
        st.caption(DESCRICOES[chave])
ui.nota_sigilo()
