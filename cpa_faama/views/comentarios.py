import pandas as pd
import streamlit as st

from cpa import auth, charts, metrics, moderacao, ui
from cpa.config import get_settings

ui.aplicar_estilo()
MIN = get_settings().min_respondentes
usuario = auth.usuario_atual()
e_admin = usuario is not None and usuario.perfil == "admin"
df, meta = ui.base_do_usuario()
ui.cabecalho("Comentários dos Alunos", "Textos livres, sem identificação do aluno", meta)
if df.empty:
    ui.sem_dados()

base = ui.filtros(df, [("AVALIACAO", "Tipo de avaliação"), ("NOME_CURSO", "Curso"),
                       ("NOME_PROFESSOR", "Professor")], "com")
dados, _ = ui.filtro_semestre(base, "com")
cfg = moderacao.carregar()
todos = moderacao.preparar_comentarios(dados, MIN, cfg)

COLUNAS = {"AVALIACAO": "Avaliação", "NOME_CURSO": "Curso", "NOME_PROFESSOR": "Professor",
           "NOME_DISCIPLINA": "Disciplina", "COMENTARIO_EXIBIDO": "Comentário"}


def lista_comentarios() -> None:
    visiveis = todos[todos["VISIVEL"]]
    busca = st.text_input("🔎 Buscar nos comentários", placeholder="Ex.: biblioteca, avaliação, wi-fi")
    if busca:
        visiveis = visiveis[visiveis["COMENTARIO_EXIBIDO"].str.contains(busca, case=False, regex=False, na=False)]

    moderados = todos["SIGILO_OK"] & ~todos["MODERACAO"].isin(moderacao.VISIVEIS)
    ui.cartoes([
        ("Comentários exibidos", ui.num(len(visiveis)), None, None),
        ("Ocultos por sigilo", ui.num(int((~todos["SIGILO_OK"]).sum())), None,
         f"Grupos com menos de {MIN} respondentes."),
        ("Removidos pela moderação", ui.num(int(moderados.sum())), None,
         "Sem conteúdo (ex.: \".\"), palavrões ou ocultados manualmente pela CPA."),
    ])
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Termos mais citados")
        st.plotly_chart(charts.termos(metrics.termos_frequentes(visiveis["COMENTARIO_EXIBIDO"])), width="stretch")
    with c2:
        st.subheader("Comentários")
        agrupar = st.toggle("Agrupar comentários repetidos", value=True,
                            help="O mesmo aluno costuma colar o mesmo texto em cada disciplina do professor. "
                                 "Agrupado, o comentário aparece uma vez com as disciplinas juntas.")
        tabela = visiveis[list(COLUNAS)]
        if agrupar and not tabela.empty:
            tabela = (tabela.groupby(["AVALIACAO", "NOME_CURSO", "NOME_PROFESSOR", "COMENTARIO_EXIBIDO"], sort=False)
                      .agg(NOME_DISCIPLINA=("NOME_DISCIPLINA", lambda s: " · ".join(dict.fromkeys(s))),
                           VEZES=("NOME_DISCIPLINA", "size"))
                      .reset_index()[["AVALIACAO", "NOME_CURSO", "NOME_PROFESSOR", "NOME_DISCIPLINA", "VEZES",
                                      "COMENTARIO_EXIBIDO"]])
        st.dataframe(tabela.rename(columns={**COLUNAS, "VEZES": "Vezes"}), hide_index=True, width="stretch",
                     height=520, column_config={"Comentário": st.column_config.TextColumn(width="large")})
    st.markdown("<div class='nota-sigilo'>Os comentários passam pelo filtro de moderação da CPA. Antes de "
                "compartilhar, verifique se algum texto permite identificar o aluno.</div>", unsafe_allow_html=True)
    if e_admin and not visiveis.empty:
        st.write("")
        ui.botao_excel({"Comentários": visiveis[list(COLUNAS)]}, "cpa_comentarios.xlsx", "xls_com")


def tela_moderacao() -> None:
    st.markdown("Aqui a CPA define o que pode ou não aparecer. As regras valem para **todas as telas** "
                "(coordenadores e professores veem só os comentários aprovados).")
    resumo = todos["MODERACAO"].value_counts()
    ui.cartoes([(rotulo, ui.num(int(resumo.get(rotulo, 0))), None, None) for rotulo in
                (moderacao.APROVADO, moderacao.SEM_CONTEUDO, moderacao.PALAVRAO, moderacao.MASCARADO, moderacao.MANUAL)])

    with st.expander("⚙️ Regras do filtro", expanded=False):
        with st.form("regras_moderacao"):
            modo = st.radio("Quando encontrar uma palavra bloqueada", ["ocultar", "mascarar"], horizontal=True,
                            index=0 if cfg["modo"] == "ocultar" else 1,
                            format_func=lambda m: "Ocultar o comentário inteiro" if m == "ocultar"
                            else "Mostrar o comentário trocando a palavra por ***")
            minimo = st.number_input("Mínimo de letras para um comentário ser exibido", 1, 30,
                                     int(cfg["minimo_letras"]),
                                     help="Remove textos como \".\", \"-\" ou \"ok\".")
            c1, c2 = st.columns(2)
            palavras = c1.text_area("Palavras bloqueadas (uma por linha)", "\n".join(cfg["palavras_bloqueadas"]),
                                    height=260, help="Termine com * para pegar variações: fod* pega foda, fodido…")
            vazios = c2.text_area("Respostas consideradas sem conteúdo (uma por linha)",
                                  "\n".join(cfg["respostas_sem_conteudo"]), height=260)
            if st.form_submit_button("Salvar regras", type="primary"):
                moderacao.salvar({**cfg, "modo": modo, "minimo_letras": int(minimo),
                                  "palavras_bloqueadas": palavras.splitlines(),
                                  "respostas_sem_conteudo": vazios.splitlines()})
                st.success("Regras salvas.")
                st.rerun()

    with st.expander("🧪 Testar um texto"):
        teste = st.text_input("Digite um comentário para ver como o filtro trata")
        if teste:
            situacao, exibido = moderacao.classificar(teste, cfg)
            st.write(f"**Situação:** {situacao}")
            if exibido:
                st.write(f"**Como aparece:** {exibido}")

    st.subheader("Revisão dos comentários")
    filtro = st.radio("Mostrar", ["Sinalizados pelo filtro", "Ocultos pela CPA", "Todos"], horizontal=True)
    revisao = todos
    if filtro == "Sinalizados pelo filtro":
        revisao = todos[todos["MODERACAO"].isin([moderacao.SEM_CONTEUDO, moderacao.PALAVRAO, moderacao.MASCARADO])]
    elif filtro == "Ocultos pela CPA":
        revisao = todos[todos["MODERACAO"] == moderacao.MANUAL]
    if revisao.empty:
        st.info("Nenhum comentário nesta situação.")
        return
    editor = pd.DataFrame({
        "Ocultar": revisao["MODERACAO"] == moderacao.MANUAL,
        "Situação": revisao["MODERACAO"],
        "Comentário original": revisao["COMENTARIO"],
        "Avaliação": revisao["AVALIACAO"], "Curso": revisao["NOME_CURSO"], "Professor": revisao["NOME_PROFESSOR"],
        "_chave": revisao["CHAVE"],
    }).reset_index(drop=True)
    st.caption("Marque **Ocultar** para esconder um comentário específico (por exemplo, um texto que identifica "
               "o aluno ou ofende alguém sem usar palavrão) e clique em salvar.")
    editado = st.data_editor(editor, hide_index=True, width="stretch", height=480,
                             column_order=["Ocultar", "Situação", "Comentário original", "Avaliação", "Curso", "Professor"],
                             disabled=["Situação", "Comentário original", "Avaliação", "Curso", "Professor"],
                             column_config={"Comentário original": st.column_config.TextColumn(width="large")},
                             key=f"editor_{filtro}")
    if st.button("Salvar ocultações", type="primary"):
        ocultos = set(cfg["ocultos_manualmente"])
        ocultos -= set(editado.loc[~editado["Ocultar"], "_chave"])
        ocultos |= set(editado.loc[editado["Ocultar"], "_chave"])
        moderacao.salvar({**cfg, "ocultos_manualmente": sorted(ocultos)})
        st.success("Alterações salvas.")
        st.rerun()


if e_admin:
    aba_lista, aba_mod = st.tabs(["💬 Comentários", "🛡️ Moderação"])
    with aba_lista:
        lista_comentarios()
    with aba_mod:
        tela_moderacao()
else:
    lista_comentarios()
