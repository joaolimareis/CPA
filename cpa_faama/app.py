"""Sistema interno da CPA. Execute com: streamlit run app.py"""
import logging
import time

import streamlit as st

from cpa import acessos, auth, ui
from cpa.config import RAIZ, get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
s = get_settings()
LOGO = RAIZ / "assets" / "logo.png"
st.set_page_config(page_title=f"CPA {s.nome_instituicao}", page_icon=str(RAIZ / "assets" / "favicon.png")
                   if (RAIZ / "assets" / "favicon.png").exists() else "📊", layout="wide")
ui.aplicar_estilo()
if LOGO.exists():
    st.logo(str(LOGO), size="large")

usuario = auth.usuario_atual()

# Sessão: sai sozinho após X minutos sem uso, ou se o acesso venceu (ex.: avaliador externo)
if usuario is not None:
    parado = time.time() - st.session_state.get("ultimo_uso", time.time())
    if parado > s.sessao_minutos * 60 or usuario.expirado:
        acessos.registrar("sessão encerrada", usuario.login, "inatividade" if not usuario.expirado else "acesso vencido")
        st.session_state.pop("usuario", None)
        usuario = None
        st.info("Sua sessão foi encerrada. Entre novamente.")
    else:
        st.session_state["ultimo_uso"] = time.time()

if usuario is None:
    auth.tela_login()
    st.stop()

from cpa.navegacao import GRUPOS_POR_PERFIL, PAGINAS  # noqa: E402

menu = {}
primeira = True
for grupo, chaves in GRUPOS_POR_PERFIL[usuario.perfil].items():
    menu[grupo] = []
    for c in chaves:
        caminho, titulo, icone = PAGINAS[c]
        menu[grupo].append(st.Page(caminho, title=titulo, icon=icone, default=primeira))
        primeira = False

with st.sidebar:
    st.markdown(f"**{usuario.nome}**  \n{usuario.descricao_perfil}")
    if usuario.perfil == "coordenador":
        st.caption("Cursos: " + ", ".join(usuario.cursos))
    if usuario.valido_ate:
        st.caption(f"Acesso válido até {usuario.valido_ate[8:10]}/{usuario.valido_ate[5:7]}/{usuario.valido_ate[:4]}")
    if st.button("Sair", use_container_width=True):
        acessos.registrar("logout", usuario.login)
        auth.sair()
    st.divider()

pagina = st.navigation(menu)
if st.session_state.get("ultima_pagina") != pagina.title:
    st.session_state["ultima_pagina"] = pagina.title
    acessos.registrar("página", usuario.login, pagina.title)
pagina.run()
