"""Login, perfis de acesso e filtro de escopo (o que cada usuário pode ver)."""
from __future__ import annotations

import time
from datetime import date
from dataclasses import asdict, dataclass, field
from pathlib import Path

import bcrypt
import pandas as pd
import streamlit as st
import yaml

from cpa.config import get_settings
from cpa.processing import DOCENTE

PERFIS = {
    "admin": "CPA / Administração",
    "coordenador": "Coordenação de curso",
    "professor": "Professor(a)",
    "avaliador": "Avaliador externo (somente leitura)",
}


@dataclass(frozen=True)
class Usuario:
    login: str
    nome: str
    perfil: str
    cursos: tuple[str, ...] = field(default_factory=tuple)
    codprof: str | None = None
    valido_ate: str | None = None

    @property
    def expirado(self) -> bool:
        """Acesso com data de validade (ex.: avaliadores externos) vence no fim do dia informado."""
        if not self.valido_ate:
            return False
        try:
            return date.today() > date.fromisoformat(str(self.valido_ate))
        except ValueError:
            return True

    @property
    def descricao_perfil(self) -> str:
        return PERFIS.get(self.perfil, self.perfil)


def carregar_usuarios(caminho: Path | None = None) -> dict[str, dict]:
    caminho = caminho or get_settings().arquivo_usuarios
    if not caminho.exists():
        return {}
    conteudo = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    return conteudo.get("usuarios", {}) or {}


def _montar(login: str, dados: dict) -> Usuario:
    return Usuario(
        login=login,
        nome=dados.get("nome", login),
        perfil=dados.get("perfil", ""),
        cursos=tuple(dados.get("cursos") or ()),
        codprof=str(dados["codprof"]) if dados.get("codprof") is not None else None,
        valido_ate=str(dados["valido_ate"]) if dados.get("valido_ate") else None,
    )


def autenticar(login: str, senha: str, usuarios: dict[str, dict] | None = None) -> Usuario | None:
    usuarios = carregar_usuarios() if usuarios is None else usuarios
    dados = usuarios.get(login.strip().lower())
    if not dados or dados.get("ativo") is False:
        return None
    hash_salvo = str(dados.get("senha_hash", "")).encode()
    try:
        if not bcrypt.checkpw(senha.encode(), hash_salvo):
            return None
    except ValueError:
        return None
    usuario = _montar(login.strip().lower(), dados)
    if usuario.perfil not in PERFIS or usuario.expirado:
        return None
    return usuario


def gerar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=12)).decode()


# ---------- sessão (Streamlit) ----------

def usuario_atual() -> Usuario | None:
    dados = st.session_state.get("usuario")
    return Usuario(**{**dados, "cursos": tuple(dados.get("cursos", ()))}) if dados else None


def sair() -> None:
    st.session_state.pop("usuario", None)
    st.rerun()


def tela_login() -> None:
    from cpa import acessos
    from cpa.ui import logo_base64

    s = get_settings()
    _, centro, _ = st.columns([1, 1.1, 1])
    with centro:
        logo = logo_base64()
        img = f"<img src='data:image/png;base64,{logo}' alt='FAAMA'>" if logo else ""
        st.markdown(f"<div class='login-caixa'>{img}<div class='login-titulo'>Avaliação Institucional</div>"
                    f"<p style='color:#4A5B6E;margin:0'>Comissão Própria de Avaliação · {s.nome_instituicao}</p></div>",
                    unsafe_allow_html=True)
        st.write("")
        if not carregar_usuarios():
            st.error("Nenhum usuário cadastrado. Crie o primeiro com: "
                     "`python scripts/criar_usuario.py cpa --perfil admin`")
            return
        with st.form("login"):
            login = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        st.caption("Acesso restrito. As respostas dos alunos são anônimas.")
        if entrar:
            tentativas = st.session_state.get("tentativas", 0)
            if tentativas >= 5:
                time.sleep(3)  # desacelera tentativas repetidas
            usuario = autenticar(login, senha)
            if usuario:
                st.session_state["tentativas"] = 0
                st.session_state["usuario"] = asdict(usuario)
                st.session_state["ultimo_uso"] = time.time()
                acessos.registrar("login", usuario.login, usuario.descricao_perfil)
                st.rerun()
            else:
                st.session_state["tentativas"] = tentativas + 1
                acessos.registrar("login recusado", login.strip().lower())
                st.error("Usuário ou senha inválidos, ou acesso vencido.")


# ---------- escopo de dados ----------

def aplicar_escopo(df: pd.DataFrame, usuario: Usuario | None) -> pd.DataFrame:
    """Recorta a base conforme o perfil. É aplicado antes de qualquer tela."""
    if usuario is None:
        return df.iloc[0:0]
    if usuario.perfil in ("admin", "avaliador"):
        return df
    if usuario.perfil == "coordenador":
        return df[df["NOME_CURSO"].isin(usuario.cursos).fillna(False)]
    if usuario.perfil == "professor" and usuario.codprof:
        mask = df["TIPO_AVALIACAO"].eq(DOCENTE).fillna(False) & df["CODPROF"].eq(usuario.codprof).fillna(False)
        return df[mask]
    return df.iloc[0:0]
