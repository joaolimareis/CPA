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

st.subheader("Usuários e acessos")
usuarios = auth.carregar_usuarios()
st.dataframe(pd.DataFrame([{
    "Usuário": login, "Nome": d.get("nome"), "Perfil": auth.PERFIS.get(d.get("perfil"), d.get("perfil")),
    "Cursos": ", ".join(d.get("cursos") or []), "Cód. professor": d.get("codprof"),
    "Válido até": d.get("valido_ate"), "Ativo": "Sim" if d.get("ativo", True) else "Não"}
    for login, d in usuarios.items()]), hide_index=True, width="stretch")

with st.expander("➕ Criar ou alterar um usuário", expanded=False):
    existentes = ["(novo usuário)"] + sorted(usuarios)
    escolhido = st.selectbox("Usuário", existentes, key="adm_usr_sel")
    atual = usuarios.get(escolhido, {}) if escolhido != "(novo usuário)" else {}
    cursos_base = sorted(df["NOME_CURSO"].dropna().unique())
    perfis = list(auth.PERFIS)
    with st.form("form_usuario", clear_on_submit=False):
        c1, c2 = st.columns(2)
        login_novo = c1.text_input("Login", value="" if not atual else escolhido, disabled=bool(atual),
                                   help="Sem espaços. Ex.: coord.direito")
        nome = c2.text_input("Nome", value=atual.get("nome", ""))
        perfil = c1.selectbox("Perfil", perfis, index=perfis.index(atual.get("perfil", "coordenador")),
                              format_func=lambda p: auth.PERFIS[p])
        cursos_sel = c2.multiselect("Cursos (para coordenador)", cursos_base,
                                    default=[c for c in atual.get("cursos", []) if c in cursos_base])
        codprof = c1.text_input("Código do professor no TOTVS (para professor)", value=str(atual.get("codprof") or ""))
        tem_validade = c2.checkbox("Acesso com data de validade", value=bool(atual.get("valido_ate")))
        from datetime import date, timedelta
        validade = c2.date_input("Válido até", value=date.fromisoformat(atual["valido_ate"]) if atual.get("valido_ate")
                                 else date.today() + timedelta(days=30), format="DD/MM/YYYY")
        senha = c1.text_input("Senha" + (" (deixe em branco para manter a atual)" if atual else ""), type="password")
        senha2 = c2.text_input("Repita a senha", type="password")
        ativo = st.checkbox("Ativo", value=atual.get("ativo", True))
        if st.form_submit_button("Salvar usuário", type="primary"):
            login_final = escolhido if atual else login_novo
            if senha != senha2:
                st.error("As senhas não conferem.")
            elif login_final.strip().lower() == usuario.login and (not ativo or perfil != "admin"):
                st.error("Você não pode desativar nem tirar o perfil de administrador do seu próprio usuário.")
            else:
                try:
                    auth.salvar_usuario(login_final, nome, perfil, senha or None, cursos_sel, codprof or None,
                                        validade.isoformat() if tem_validade else None, ativo)
                    acessos.registrar("usuário salvo", usuario.login, login_final)
                    st.success(f"Usuário {login_final} salvo.")
                    st.rerun()
                except ValueError as erro:
                    st.error(str(erro))
st.caption("Dica: para a visita do MEC, crie um usuário com perfil Avaliador externo e data de validade.")

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
