"""Tratamento dos dados da API: as mesmas regras usadas no Power Query do relatório."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

COLUNAS_API = [
    "TIPO_AVALIACAO", "PERIODO_PROVA", "SEMESTRE", "CODPERLET", "CODCURSO", "NOME_CURSO",
    "CODTURMA", "NOME_TURMA", "STATUS_MATRICULA", "ID_RESPONDENTE", "CODPROVA", "NOME_PROVA",
    "CODPROF", "NOME_PROFESSOR", "CODDISC", "NOME_DISCIPLINA", "CODMATERIA", "CODQUESTAO",
    "DESC_QUESTAO", "CODRESPOSTA", "TEXTO_ALTERNATIVA", "COMENTARIO", "TIPO_RESPOSTA",
]

ESCALA_CONCORDANCIA = {
    "Concordo totalmente": 5,
    "Concordo parcialmente": 4,
    "Indiferente / Neutro": 3,
    "Discordo parcialmente": 2,
    "Discordo totalmente": 1,
}
INDICACAO = ("Sim, sem reservas", "Sim, com algumas ressalvas", "Não")

FAVORAVEL, NEUTRO, DESFAVORAVEL, NAO_SE_APLICA = "Favorável", "Neutro", "Desfavorável", "Não se aplica"
GRUPOS_VALIDOS = [FAVORAVEL, NEUTRO, DESFAVORAVEL]
ORDEM_GRUPOS = [FAVORAVEL, NEUTRO, DESFAVORAVEL, NAO_SE_APLICA]

# TIPO_AVALIACAO como vem da consulta SQL
DOCENTE = "DOCENTE_DISCIPLINA"
CURSO_INFRA_SQL = "CURSO_INFRAESTRUTURA"

# TIPO_PROVA: classificação usada no sistema (curso e infraestrutura ficam separados)
PROVA_DOCENTE, PROVA_CURSO, PROVA_INFRA = "DOCENTE", "CURSO", "INFRAESTRUTURA"
ROTULO_PROVA = {PROVA_DOCENTE: "Docente e Disciplina", PROVA_CURSO: "Avaliação do Curso",
                PROVA_INFRA: "Infraestrutura"}

COLUNAS_OPCIONAIS = ["DATA_RESPOSTA", "ULTIMA_AVALIACAO", "SEMESTRE_DISCIPLINA"]
MOTIVO_SEMESTRE_ANTERIOR = "Professor de semestre anterior"
MOTIVO_REPETIDA = "Avaliação repetida"  # entra automaticamente se for incluída na consulta SQL


def _igual(serie: pd.Series, valor: str) -> pd.Series:
    """Comparação segura com valores nulos (nulo conta como False)."""
    return serie.eq(valor).fillna(False).astype(bool)


def classificar_prova(df: pd.DataFrame, provas_infra: Iterable[str] = (),
                      palavra_infra: str = "Infraestrutura") -> pd.Series:
    """Separa as provas em DOCENTE, CURSO e INFRAESTRUTURA.

    Se PROVAS_INFRAESTRUTURA (códigos) estiver configurado, usa os códigos;
    senão, procura a palavra no nome da prova.
    """
    codigos = [str(c) for c in provas_infra]
    if codigos:
        e_infra = df["CODPROVA"].isin(codigos).fillna(False).astype(bool)
    else:
        e_infra = df["NOME_PROVA"].str.contains(palavra_infra, case=False, regex=False).fillna(False).astype(bool)
    e_docente = _igual(df["TIPO_AVALIACAO"], DOCENTE)
    tipo = np.select([e_docente, e_infra], [PROVA_DOCENTE, PROVA_INFRA], default=PROVA_CURSO)
    return pd.Series(tipo, index=df.index, dtype="string")


def processar(dados: Iterable[dict] | pd.DataFrame,
              cursos_excluidos: Iterable[str] = (),
              provas_infra: Iterable[str] = (),
              palavra_infra: str = "Infraestrutura",
              relatorio: dict | None = None,
              cursos_permitidos: Iterable[str] = (),
              descartes: list | None = None,
              questoes_anuladas: Iterable[str] = ()) -> pd.DataFrame:
    """Recebe os registros crus da API e devolve a base pronta para análise.

    Se `relatorio` for informado, recebe a contagem de linhas de cada etapa (usado na Auditoria).
    """
    relatorio = relatorio if relatorio is not None else {}
    df = dados.copy() if isinstance(dados, pd.DataFrame) else pd.DataFrame(list(dados))
    if df.empty:
        df = pd.DataFrame(columns=COLUNAS_API)
    faltando = [c for c in COLUNAS_API if c not in df.columns]
    if faltando:
        raise ValueError(f"A consulta da API não trouxe as colunas: {', '.join(faltando)}")

    relatorio["linhas_api"] = len(df)
    opcionais = [c for c in COLUNAS_OPCIONAIS if c in df.columns]
    extras = df[opcionais].copy()
    df = df[COLUNAS_API].astype("string")
    # Remove quebras de linha, tabulações e espaços duplicados de todos os textos
    for coluna in COLUNAS_API:
        df[coluna] = df[coluna].str.replace(r"\s+", " ", regex=True).str.strip()
        df[coluna] = df[coluna].mask(df[coluna] == "")

    if "DATA_RESPOSTA" in extras:
        df["DATA_RESPOSTA"] = pd.to_datetime(extras["DATA_RESPOSTA"], errors="coerce")

    excluidos, permitidos = list(cursos_excluidos), list(cursos_permitidos)
    antes = len(df)
    if permitidos:  # lista fechada: só estes cursos entram
        df = df[df["NOME_CURSO"].isin(permitidos).fillna(False)]
    if excluidos:
        df = df[~df["NOME_CURSO"].isin(excluidos).fillna(False)]
    relatorio["removidas_cursos_excluidos"] = antes - len(df)

    # Textos informativos da CPA (apresentação e agradecimento): resposta "ENTENDI"
    informativo = df["CODRESPOSTA"].fillna("").str.upper().str.startswith("ENTENDI")
    relatorio["removidas_textos_informativos"] = int(informativo.sum())
    df = df[~informativo].copy()

    # Questões aplicadas por engano numa prova (anuladas no RM), no formato "prova:matéria:questão"
    anuladas = {str(q).strip() for q in questoes_anuladas if str(q).strip()}
    relatorio["removidas_questoes_anuladas"] = 0
    if anuladas:
        chave = df["CODPROVA"].fillna("") + ":" + df["CODMATERIA"].fillna("") + ":" + df["CODQUESTAO"].fillna("")
        e_anulada = chave.isin(anuladas)
        relatorio["removidas_questoes_anuladas"] = int(e_anulada.sum())
        df = df[~e_anulada].copy()

    # Avaliações docentes que não devem contar (guardadas com o motivo para a página de Validação):
    # 1) professor de disciplina de outro semestre; 2) avaliação repetida (vale só a mais recente)
    motivo = pd.Series(pd.NA, index=df.index, dtype="string")
    if "SEMESTRE_DISCIPLINA" in extras:
        sem_disc = extras.loc[df.index, "SEMESTRE_DISCIPLINA"].astype("string").str.strip()
        df["SEMESTRE_DISCIPLINA"] = sem_disc
        outro = sem_disc.notna() & (sem_disc.str[:6] != df["SEMESTRE"].fillna("").str[:6])
        motivo = motivo.mask(outro.fillna(False).astype(bool), MOTIVO_SEMESTRE_ANTERIOR)
    if "ULTIMA_AVALIACAO" in extras:
        ultima = pd.to_numeric(extras.loc[df.index, "ULTIMA_AVALIACAO"], errors="coerce")
        atual = pd.to_numeric(df["ID_RESPONDENTE"], errors="coerce")
        repetida = ultima.notna() & atual.notna() & (ultima != atual)
        motivo = motivo.mask(motivo.isna() & repetida, MOTIVO_REPETIDA)
    descartar = motivo.notna().to_numpy()
    relatorio["removidas_semestre_anterior"] = int((motivo == MOTIVO_SEMESTRE_ANTERIOR).sum())
    relatorio["removidas_avaliacoes_repetidas"] = int((motivo == MOTIVO_REPETIDA).sum())
    if descartes is not None and descartar.any():
        descartes.append(df[descartar].assign(MOTIVO_DESCARTE=motivo[descartar]).reset_index(drop=True))
    df = df[~descartar].copy()

    df["TIPO_PROVA"] = classificar_prova(df, provas_infra, palavra_infra)
    df["AVALIACAO"] = df["TIPO_PROVA"].map(ROTULO_PROVA).astype("string")

    alternativa = df["TEXTO_ALTERNATIVA"]
    objetiva = _igual(df["TIPO_RESPOSTA"], "OBJETIVA")
    e_nota = objetiva & _igual(alternativa, ".")  # questão de nota global (1 a 5)
    e_indicacao = objetiva & alternativa.isin(INDICACAO).fillna(False).astype(bool)

    escala = np.select([e_nota, e_indicacao, objetiva],
                       ["Nota global", "Indicação", "Concordância"], default="")
    df["ESCALA"] = pd.Series(escala, index=df.index, dtype="string").mask(lambda s: s == "")

    nota_global = pd.to_numeric(df["CODRESPOSTA"], errors="coerce")
    nota_global = nota_global.where(nota_global.between(1, 5))
    nota_concordancia = alternativa.map(ESCALA_CONCORDANCIA).astype("float64")
    e_concordancia = _igual(df["ESCALA"], "Concordância")
    df["NOTA"] = np.where(e_nota, nota_global, np.where(e_concordancia, nota_concordancia, np.nan))

    df["ALTERNATIVA"] = alternativa.where(~e_nota, "Nota " + df["CODRESPOSTA"].fillna(""))

    nota = df["NOTA"]
    grupo = np.select(
        [df["ESCALA"].isna().to_numpy(),
         (e_indicacao & _igual(alternativa, "Não")).to_numpy(),
         e_indicacao.to_numpy(),
         nota.isna().to_numpy(),
         (nota >= 4).to_numpy(),
         (nota == 3).to_numpy()],
        ["", DESFAVORAVEL, FAVORAVEL, NAO_SE_APLICA, FAVORAVEL, NEUTRO],
        default=DESFAVORAVEL,
    )
    df["GRUPO"] = pd.Series(grupo, index=df.index, dtype="string").mask(lambda s: s == "")

    df["VALIDA"] = df["GRUPO"].isin(GRUPOS_VALIDOS).fillna(False).astype(int)
    df["FAVORAVEL"] = _igual(df["GRUPO"], FAVORAVEL).astype(int)
    df["NEUTRO"] = _igual(df["GRUPO"], NEUTRO).astype(int)
    df["DESFAVORAVEL"] = _igual(df["GRUPO"], DESFAVORAVEL).astype(int)
    df["E_COMENTARIO"] = _igual(df["TIPO_RESPOSTA"], "DISSERTATIVA").astype(int)

    relatorio["linhas_finais"] = len(df)
    return df.reset_index(drop=True)
