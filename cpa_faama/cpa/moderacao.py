"""Moderação dos comentários: remove textos sem conteúdo, filtra palavrões e permite ocultar manualmente.

As regras ficam em config/moderacao.yaml e podem ser editadas pela CPA na página de Comentários.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from functools import lru_cache

import pandas as pd
import yaml

from cpa.config import get_settings

APROVADO = "Aprovado"
MASCARADO = "Palavrão (mascarado)"
PALAVRAO = "Palavrão (oculto)"
SEM_CONTEUDO = "Sem conteúdo"
MANUAL = "Oculto pela CPA"
VISIVEIS = {APROVADO, MASCARADO}

# Lista inicial. Termos terminados em * pegam variações (ex.: "fod*" pega foda, fodido, foder).
# Revise e complete na tela de moderação conforme a realidade dos comentários.
PALAVRAS_PADRAO = [
    "porr*", "caralh*", "merd*", "bost*", "puta", "puto", "putaria", "fdp", "vsf", "pqp", "tnc",
    "fod*", "cu", "cuzao", "arromb*", "buceta", "desgrac*", "vagabund*", "otari*", "idiota*",
    "imbecil*", "babaca*", "retardad*", "escrot*", "viado", "viadinho", "corno*", "piranha*", "safad*",
]
SEM_CONTEUDO_PADRAO = ["nada", "nenhum", "nenhuma", "n/a", "na", "ok", "nao", "sem comentarios",
                       "sem comentario", "nada a declarar", "nada a acrescentar", "-", "sem sugestoes"]

PADRAO = {
    "modo": "ocultar",            # "ocultar" esconde o comentário; "mascarar" troca a palavra por ***
    "minimo_letras": 3,           # comentários com menos letras que isso são "sem conteúdo" (ex.: ".")
    "palavras_bloqueadas": PALAVRAS_PADRAO,
    "respostas_sem_conteudo": SEM_CONTEUDO_PADRAO,
    "ocultos_manualmente": [],    # chaves (hash) dos comentários ocultados pela CPA
}


# ---------- configuração ----------

def carregar() -> dict:
    caminho = get_settings().arquivo_moderacao
    if not caminho.exists():
        salvar(PADRAO)
        return dict(PADRAO)
    conteudo = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    return {**PADRAO, **conteudo}


def salvar(cfg: dict) -> None:
    caminho = get_settings().arquivo_moderacao
    caminho.parent.mkdir(parents=True, exist_ok=True)
    limpo = {**PADRAO, **cfg}
    limpo["palavras_bloqueadas"] = sorted({p.strip().lower() for p in limpo["palavras_bloqueadas"] if p.strip()})
    limpo["respostas_sem_conteudo"] = sorted({p.strip().lower() for p in limpo["respostas_sem_conteudo"] if p.strip()})
    limpo["ocultos_manualmente"] = sorted(set(limpo["ocultos_manualmente"]))
    caminho.write_text(yaml.safe_dump(limpo, allow_unicode=True, sort_keys=False), encoding="utf-8")


# ---------- classificação ----------

def normalizar(texto: str) -> str:
    """Minúsculas e sem acento, mantendo o mesmo tamanho do texto (para poder mascarar)."""
    return "".join(unicodedata.normalize("NFKD", c)[0] for c in texto).lower()


@lru_cache(maxsize=32)
def _regex(palavras: tuple[str, ...]) -> re.Pattern | None:
    partes = []
    for p in palavras:
        p = normalizar(p.strip())
        if not p:
            continue
        if p.endswith("*"):
            partes.append(r"\b" + re.escape(p[:-1]) + r"\w*")
        else:
            partes.append(r"\b" + re.escape(p) + r"\b")
    return re.compile("|".join(partes)) if partes else None


def chave(id_respondente, codmateria, codquestao) -> str:
    """Identificador estável do comentário (não identifica o aluno)."""
    return hashlib.sha1(f"{id_respondente}|{codmateria}|{codquestao}".encode()).hexdigest()[:12]


def sem_conteudo(texto: str, cfg: dict) -> bool:
    letras = sum(c.isalpha() for c in texto)
    if letras < int(cfg.get("minimo_letras", 3)):
        return True
    simples = re.sub(r"[^\w\s/]", "", normalizar(texto)).strip()
    return simples in {normalizar(t) for t in cfg.get("respostas_sem_conteudo", [])}


def classificar(texto: str | None, cfg: dict, oculto_manual: bool = False) -> tuple[str, str]:
    """Devolve (situação, texto a exibir)."""
    if oculto_manual:
        return MANUAL, ""
    texto = "" if texto is None or pd.isna(texto) else str(texto).strip()
    if sem_conteudo(texto, cfg):
        return SEM_CONTEUDO, ""
    padrao = _regex(tuple(cfg.get("palavras_bloqueadas", [])))
    if padrao is None:
        return APROVADO, texto
    achados = list(padrao.finditer(normalizar(texto)))
    if not achados:
        return APROVADO, texto
    if cfg.get("modo") == "mascarar":
        resultado = list(texto)
        for m in achados:
            for i in range(m.start(), m.end()):
                resultado[i] = "*"
        return MASCARADO, "".join(resultado)
    return PALAVRAO, ""


def aplicar(comentarios: pd.DataFrame, cfg: dict | None = None) -> pd.DataFrame:
    """Acrescenta CHAVE, MODERACAO, COMENTARIO_EXIBIDO e VISIVEL aos comentários."""
    cfg = cfg or carregar()
    df = comentarios.copy()
    if df.empty:
        for c in ("CHAVE", "MODERACAO", "COMENTARIO_EXIBIDO"):
            df[c] = pd.Series(dtype="string")
        df["VISIVEL"] = pd.Series(dtype=bool)
        return df
    ocultos = set(cfg.get("ocultos_manualmente", []))
    df["CHAVE"] = [chave(a, b, c) for a, b, c in zip(df["ID_RESPONDENTE"], df["CODMATERIA"], df["CODQUESTAO"])]
    resultado = [classificar(t, cfg, k in ocultos) for t, k in zip(df["COMENTARIO"], df["CHAVE"])]
    df["MODERACAO"] = [r[0] for r in resultado]
    df["COMENTARIO_EXIBIDO"] = [r[1] for r in resultado]
    df["VISIVEL"] = df["MODERACAO"].isin(VISIVEIS)
    return df


def preparar_comentarios(dados: pd.DataFrame, min_respondentes: int, cfg: dict | None = None) -> pd.DataFrame:
    """Todos os comentários do recorte, com sigilo e moderação aplicados.

    Colunas extras: SIGILO_OK (grupo tem respondentes suficientes), MODERACAO, VISIVEL (passa nos dois).
    """
    chaves = ["AVALIACAO", "NOME_CURSO", "NOME_PROFESSOR", "NOME_DISCIPLINA"]
    if dados.empty:
        base = dados.iloc[0:0].copy()
        base["SIGILO_OK"] = pd.Series(dtype=bool)
        return aplicar(base, cfg)
    base = dados.copy()
    base[chaves] = base[chaves].fillna("—")
    base["_n"] = base.groupby(chaves)["ID_RESPONDENTE"].transform("nunique")
    comentarios = base[base["E_COMENTARIO"] == 1].copy()
    comentarios["SIGILO_OK"] = comentarios["_n"] >= min_respondentes
    comentarios = aplicar(comentarios.drop(columns="_n"), cfg)
    comentarios["VISIVEL"] = comentarios["VISIVEL"] & comentarios["SIGILO_OK"]
    return comentarios
