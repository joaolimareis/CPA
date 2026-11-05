import pandas as pd
import streamlit as st

from cpa import acessos, auth, ui
from cpa.config import get_settings

ui.aplicar_estilo()
usuario = auth.usuario_atual()
if not usuario or usuario.perfil != "admin":  # defesa extra além do menu
    st.error("Acesso restrito à CPA.")
    st.stop()

s = get_settings()
df, meta = ui.carregar()
ui.cabecalho("Administração", "Atualização dos dados, qualidade da base e usuários", meta)

st.subheader("Atualização dos dados")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Linhas recebidas da API", ui.num(meta.get("linhas_api")))
c2.metric("Linhas após tratamento", ui.num(meta.get("linhas_tratadas")))
c3.metric("Questionários", ui.num(df["ID_RESPONDENTE"].nunique()))
c4.metric("Atualização automática", f"a cada {s.cache_minutos} min")
if st.button("🔄 Atualizar agora a partir da API", type="primary"):
    with st.spinner("Consultando o TOTVS…"):
        novo = ui.atualizar_dados()
    if novo.get("aviso"):
        st.error(novo["aviso"])
    else:
        st.success(f"Dados atualizados: {ui.num(novo['linhas_tratadas'])} linhas.")
        st.rerun()

st.subheader("Qualidade da base")
q1, q2 = st.columns(2)
with q1:
    st.markdown("**Questionários por semestre e tipo**")
    st.dataframe(df.pivot_table(index="SEMESTRE", columns="AVALIACAO", values="ID_RESPONDENTE",
                                aggfunc="nunique", fill_value=0), width="stretch")
with q2:
    st.markdown("**Classificação das respostas**")
    st.dataframe(df["GRUPO"].fillna("Comentário / sem resposta").value_counts().rename("Linhas"),
                 width="stretch")
nao_reconhecidas = (df["ESCALA"].eq("Concordância").fillna(False) & df["NOTA"].isna()
                    & ~df["ALTERNATIVA"].fillna("").str.startswith("Não se aplica"))
sem_classificacao = df[nao_reconhecidas]
if len(sem_classificacao):
    st.warning(f"{len(sem_classificacao)} respostas objetivas com alternativa não reconhecida. "
               "Verifique se surgiu uma nova escala de respostas.")

st.subheader("Usuários cadastrados")
usuarios = auth.carregar_usuarios()
st.dataframe(pd.DataFrame([{
    "Usuário": login, "Nome": d.get("nome"), "Perfil": auth.PERFIS.get(d.get("perfil"), d.get("perfil")),
    "Cursos": ", ".join(d.get("cursos") or []), "Cód. professor": d.get("codprof"),
    "Válido até": d.get("valido_ate"), "Ativo": d.get("ativo", True)} for login, d in usuarios.items()]),
    hide_index=True, width="stretch")
st.caption("Para incluir ou alterar usuários: `python scripts/criar_usuario.py --help`")

st.subheader("Registro de acessos")
log = acessos.ler()
if log.empty:
    st.caption("Nenhum acesso registrado ainda.")
else:
    filtro = st.multiselect("Usuário", sorted(log["usuario"].dropna().unique()), placeholder="Todos", key="adm_log_user")
    if filtro:
        log = log[log["usuario"].isin(filtro)]
    st.dataframe(log.rename(columns={"data_hora": "Data e hora", "evento": "Evento", "usuario": "Usuário",
                                     "detalhe": "Detalhe"}), hide_index=True, width="stretch", height=320)

st.subheader("Configuração")
st.json({"Consulta TOTVS": s.totvs_consulta, "Coligada": s.totvs_coligada, "Modo demonstração": s.modo_demo,
         "Mínimo de respondentes": s.min_respondentes, "Cursos excluídos": list(s.cursos_excluidos)})
