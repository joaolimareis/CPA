"""Componentes de tela compartilhados entre as páginas."""
from __future__ import annotations

import base64
from datetime import datetime
from functools import lru_cache

import pandas as pd
import streamlit as st

from cpa import auth, metrics, repository
from cpa.config import RAIZ, get_settings

AZUL = "#003B6F"


@lru_cache
def logo_base64() -> str:
    caminho = RAIZ / "assets" / "logo.png"
    return base64.b64encode(caminho.read_bytes()).decode() if caminho.exists() else ""


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stDataFrame, button, input, textarea, select {
    font-family: 'Public Sans', 'Segoe UI', Arial, sans-serif;
}
.block-container {padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1440px;}
h1, h2, h3 {color: #13263B; letter-spacing: -0.01em;}
h2, h3 {font-weight: 650;}
/* faixa do topo: o único elemento de destaque da página */
.faixa {display: flex; align-items: center; gap: 18px; background: #003B6F; color: #fff;
        padding: 18px 26px; border-radius: 14px; margin-bottom: 10px;}
.faixa img {width: 54px; height: 54px; border-radius: 50%; background: #fff; padding: 2px; flex: none;}
.faixa h1 {font-size: 1.65rem; margin: 0; color: #fff; font-weight: 700; line-height: 1.15;}
.faixa p {margin: 4px 0 0 0; color: #C9D8EA; font-size: 0.95rem; max-width: 80ch;}
.fonte {color: #5B6B7D; font-size: 0.82rem; margin: 0 0 14px 2px;}
div[data-testid="stMetric"] {background: #fff; border: 1px solid #DCE3EC; border-radius: 10px;
    padding: 14px 16px;}
div[data-testid="stMetricLabel"] p {color: #4A5B6E; font-size: 0.86rem;}
div[data-testid="stMetricValue"] {color: #003B6F; font-weight: 650;}
section[data-testid="stSidebar"] {background: #FFFFFF; border-right: 1px solid #E3E8EF;}
.login-caixa {margin-top: 10vh; text-align: center;}
.login-caixa img {width: 84px; height: 84px; border-radius: 50%;}
.login-titulo {font-size: 1.5rem; font-weight: 700; color: #003B6F; margin: 14px 0 2px 0;}
.nota-sigilo {font-size: 0.86rem; color: #3D4E61; background: #EAF0F7; padding: 9px 13px;
              border-radius: 8px; border-left: 3px solid #003B6F;}
.status-avaliacao {background: #fff; border: 1px solid #DCE3EC; border-radius: 14px; padding: 22px 26px;}
.status-avaliacao .numero {font-size: 3.2rem; font-weight: 700; color: #003B6F; line-height: 1;}
.status-avaliacao .rotulo {color: #4A5B6E; font-size: 0.95rem; margin-top: 6px;}
.status-avaliacao .barra {height: 10px; background: #E3E8EF; border-radius: 6px; margin-top: 16px; overflow: hidden;}
.status-avaliacao .barra span {display: block; height: 100%; background: #003B6F;}
@media (max-width: 640px) {
  .faixa {padding: 14px 16px;} .faixa img {width: 40px; height: 40px;} .faixa h1 {font-size: 1.25rem;}
}
</style>
"""


def aplicar_estilo() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# ---------- dados ----------

@st.cache_data(ttl=get_settings().cache_minutos * 60, show_spinner="Carregando dados da avaliação…")
def base_completa() -> tuple[pd.DataFrame, dict]:
    return repository.carregar_base()


def carregar() -> tuple[pd.DataFrame, dict]:
    """Carrega a base; se a API falhar e não houver cópia, mostra o motivo na tela."""
    try:
        return base_completa()
    except Exception as erro:  # noqa: BLE001
        st.error(f"Não foi possível carregar os dados da API do TOTVS.\n\n**Motivo:** {erro}")
        st.stop()


def descartes() -> pd.DataFrame:
    carregar()  # garante que a base (e os descartes) estão atualizados
    return repository.carregar_descartes()


def base_do_usuario() -> tuple[pd.DataFrame, dict]:
    df, meta = carregar()
    return auth.aplicar_escopo(df, auth.usuario_atual()), meta


@st.cache_data(ttl=get_settings().cache_minutos * 60, show_spinner="Carregando participação…")
def participacao_completa() -> tuple[pd.DataFrame, dict]:
    return repository.carregar_participacao()


def participacao_do_usuario() -> tuple[pd.DataFrame, dict]:
    """Participação recortada pelo perfil (coordenador vê só os próprios cursos)."""
    try:
        df, meta = participacao_completa()
    except Exception as erro:  # noqa: BLE001
        st.error(f"Não foi possível carregar a consulta de participação.\n\n**Motivo:** {erro}")
        st.stop()
    usuario = auth.usuario_atual()
    if usuario and usuario.perfil == "coordenador":
        df = df[df["NOME_CURSO"].isin(usuario.cursos)]
    elif not usuario or usuario.perfil not in ("admin", "avaliador"):
        df = df.iloc[0:0]
    return df, meta


def atualizar_dados() -> dict:
    base_completa.clear()
    participacao_completa.clear()
    _, meta = repository.carregar_base(forcar=True)
    if repository.participacao_configurada():
        try:
            repository.carregar_participacao(forcar=True)
        except Exception as erro:  # noqa: BLE001
            meta = dict(meta, aviso=f"Respostas atualizadas, mas a participação falhou: {erro}")
    return meta


# ---------- formatação ----------

def pct(v: float) -> str:
    return "—" if v is None or pd.isna(v) else f"{v:.1%}".replace(".", ",")


def num(v: float, casas: int = 0) -> str:
    if v is None or pd.isna(v):
        return "—"
    texto = f"{v:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def delta_pp(atual: float, anterior: float | None) -> str | None:
    if anterior is None or pd.isna(anterior) or pd.isna(atual):
        return None
    return f"{(atual - anterior) * 100:+.1f} p.p.".replace(".", ",")


def delta_num(atual: float, anterior: float | None, casas: int = 2) -> str | None:
    if anterior is None or pd.isna(anterior) or pd.isna(atual):
        return None
    return f"{atual - anterior:+.{casas}f}".replace(".", ",")


# ---------- layout ----------

def cabecalho(titulo: str, subtitulo: str, meta: dict | None) -> None:
    logo = logo_base64()
    img = f"<img src='data:image/png;base64,{logo}' alt='FAAMA'>" if logo else ""
    st.markdown(f"<div class='faixa'>{img}<div><h1>{titulo}</h1><p>{subtitulo}</p></div></div>",
                unsafe_allow_html=True)
    if not meta:
        return
    atualizado = datetime.fromisoformat(meta["atualizado_em"]).strftime("%d/%m/%Y às %H:%M")
    st.markdown(f"<p class='fonte'>Dados do TOTVS RM, atualizados em {atualizado}</p>", unsafe_allow_html=True)
    if meta.get("aviso"):
        st.warning(meta["aviso"])
    if meta.get("modo_demo"):
        st.info("Modo demonstração: os dados exibidos são fictícios.")


def nota_sigilo() -> None:
    n = get_settings().min_respondentes
    st.markdown(f"<div class='nota-sigilo'>🔒 Respostas anônimas. Resultados de grupos com menos de "
                f"<b>{n} respondentes</b> não são exibidos.</div>", unsafe_allow_html=True)


def filtros(df: pd.DataFrame, campos: list[tuple[str, str]], chave: str) -> pd.DataFrame:
    """Filtros em cascata na barra lateral. Vazio significa 'todos'."""
    with st.sidebar:
        st.markdown("#### Filtros")
        for coluna, rotulo in campos:
            opcoes = sorted(df[coluna].dropna().unique().tolist())
            if not opcoes:
                continue
            escolha = st.multiselect(rotulo, opcoes, key=f"{chave}_{coluna}", placeholder="Todos")
            if escolha:
                df = df[df[coluna].isin(escolha)]
    return df


def filtro_semestre(df: pd.DataFrame, chave: str) -> tuple[pd.DataFrame, list[str]]:
    semestres = sorted(df["SEMESTRE"].dropna().unique().tolist())
    if not semestres:
        return df, []
    # Abre no semestre mais recente que já tenha volume real de respostas
    # (pelo menos 10% do semestre com mais questionários), e não num semestre que acabou de começar
    volume = df.groupby("SEMESTRE")["ID_RESPONDENTE"].nunique()
    com_volume = [s for s in semestres if volume.get(s, 0) >= 0.10 * volume.max()]
    padrao = com_volume[-1] if com_volume else semestres[-1]
    with st.sidebar:
        escolha = st.multiselect("Semestre", semestres, default=[padrao], key=f"{chave}_SEMESTRE",
                                 placeholder="Todos")
    escolha = escolha or semestres
    return df[df["SEMESTRE"].isin(escolha)], escolha


def indicadores_anteriores(df_sem_filtro_semestre: pd.DataFrame, escolhidos: list[str]):
    """Indicadores do semestre anterior, para mostrar a variação nos cartões."""
    todos = sorted(df_sem_filtro_semestre["SEMESTRE"].dropna().unique().tolist())
    if len(escolhidos) != 1 or escolhidos[0] not in todos:
        return None
    i = todos.index(escolhidos[0])
    if i == 0:
        return None
    anterior = df_sem_filtro_semestre[df_sem_filtro_semestre["SEMESTRE"] == todos[i - 1]]
    return metrics.indicadores(anterior) if not anterior.empty else None


def cartoes(itens: list[tuple[str, str, str | None, str | None]]) -> None:
    """itens = (rótulo, valor, variação, ajuda)."""
    colunas = st.columns(len(itens))
    for coluna, (rotulo, valor, delta, ajuda) in zip(colunas, itens):
        inverso = "inverse" if "Desfavorável" in rotulo else "normal"
        coluna.metric(rotulo, valor, delta, delta_color=inverso, help=ajuda)


def tabela_resumo(resumo: pd.DataFrame, colunas: dict[str, str], altura: int | None = None) -> None:
    """Tabela com barras de progresso nos percentuais."""
    if resumo.empty:
        st.info("Sem dados para os filtros selecionados.")
        return
    tabela = resumo[list(colunas)].rename(columns=colunas).copy()
    config = {}
    for original, rotulo in colunas.items():
        if original.startswith(("pct_", "taxa_")) or original in ("indice_confianca", "indice", "completude", "indice_alerta"):
            tabela[rotulo] = pd.to_numeric(tabela[rotulo], errors="coerce") * 100
            config[rotulo] = st.column_config.ProgressColumn(rotulo, format="%.1f%%", min_value=0, max_value=100)
        elif original in {"nota_media", "nota_global"}:
            tabela[rotulo] = pd.to_numeric(tabela[rotulo], errors="coerce")
            config[rotulo] = st.column_config.NumberColumn(rotulo, format="%.2f")
    st.dataframe(tabela, column_config=config, hide_index=True, width="stretch", height=altura or "auto")


def botao_excel(planilhas: dict[str, pd.DataFrame], nome_arquivo: str, chave: str) -> None:
    from cpa.export import para_excel
    st.download_button("⬇️ Exportar para Excel", data=para_excel(planilhas), file_name=nome_arquivo,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=chave)


def media_instituicao_docente(semestres: list[str]) -> metrics.Indicadores | None:
    """Média da instituição (só números agregados) para comparação no painel do professor."""
    df, _ = carregar()
    base = df[(df["TIPO_AVALIACAO"] == "DOCENTE_DISCIPLINA") & df["SEMESTRE"].isin(semestres)]
    return metrics.indicadores(base) if not base.empty else None


def sem_dados() -> None:
    st.info("Não há respostas para exibir com os filtros e o perfil de acesso atuais.")
    st.stop()
