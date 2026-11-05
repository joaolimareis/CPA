"""Checagens de consistência dos dados, para conferir a base com o TOTVS."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from cpa.processing import PROVA_DOCENTE, PROVA_INFRA


@dataclass
class Checagem:
    nome: str
    problemas: int
    explicacao: str
    detalhe: pd.DataFrame
    gravidade: str = "erro"  # "erro" quando deveria ser zero; "aviso" quando pode ter explicação

    @property
    def ok(self) -> bool:
        return self.problemas == 0


def reconciliacao_por_prova(df: pd.DataFrame) -> pd.DataFrame:
    """Totais por prova e período, para comparar com a consulta 2 do arquivo sql/auditoria_totvs.sql."""
    return (df.groupby(["CODPROVA", "NOME_PROVA", "AVALIACAO", "PERIODO_PROVA"], dropna=False)
            .agg(questionarios=("ID_RESPONDENTE", "nunique"), linhas=("ID_RESPONDENTE", "size"),
                 respostas_validas=("VALIDA", "sum"), comentarios=("E_COMENTARIO", "sum"),
                 cursos=("NOME_CURSO", "nunique"))
            .reset_index()
            .sort_values(["CODPROVA", "PERIODO_PROVA"], key=lambda s: pd.to_numeric(s, errors="coerce")
                         if s.name == "CODPROVA" else s))


def checagens(df: pd.DataFrame) -> list[Checagem]:
    resultado: list[Checagem] = []

    dup = (df.groupby(["ID_RESPONDENTE", "CODMATERIA", "CODQUESTAO"]).size()
           .rename("vezes").reset_index().query("vezes > 1"))
    resultado.append(Checagem(
        "Respostas duplicadas", len(dup),
        "A mesma questão aparece mais de uma vez no mesmo questionário. Indica join duplicando linhas na consulta SQL.",
        dup))

    por_id = df.groupby("ID_RESPONDENTE").agg(cursos=("NOME_CURSO", "nunique"), tipos=("TIPO_PROVA", "nunique"),
                                              provas=("CODPROVA", "nunique")).reset_index()
    multi = por_id[(por_id["cursos"] > 1) | (por_id["tipos"] > 1) | (por_id["provas"] > 1)]
    resultado.append(Checagem(
        "Questionário com mais de um curso ou prova", len(multi),
        "Um mesmo questionário deveria pertencer a um único curso e a uma única prova.", multi))

    docente = df[df["TIPO_PROVA"] == PROVA_DOCENTE]
    prof = docente.groupby("ID_RESPONDENTE").agg(professores=("CODPROF", "nunique"),
                                                 disciplinas=("CODDISC", "nunique")).reset_index()
    prof = prof[(prof["professores"] != 1) | (prof["disciplinas"] != 1)]
    resultado.append(Checagem(
        "Avaliação docente sem professor/disciplina único", len(prof),
        "Cada avaliação docente deve apontar para exatamente um professor e uma disciplina.", prof))

    periodo = df["PERIODO_PROVA"].fillna("").str[:6]
    matricula = df["CODPERLET"].fillna("").str[:6]
    div = df.loc[periodo != matricula, ["ID_RESPONDENTE", "NOME_PROVA", "PERIODO_PROVA", "CODPERLET"]].drop_duplicates()
    resultado.append(Checagem(
        "Semestre da prova diferente do semestre da matrícula", div["ID_RESPONDENTE"].nunique(),
        "A prova de um semestre ligada à matrícula de outro semestre.", div))

    nao_reconhecidas = df[df["ESCALA"].eq("Concordância").fillna(False) & df["NOTA"].isna()
                          & ~df["ALTERNATIVA"].fillna("").str.startswith("Não se aplica")]
    resultado.append(Checagem(
        "Alternativas não reconhecidas", len(nao_reconhecidas),
        "Respostas objetivas com texto fora da escala conhecida. Pode ser uma escala nova no questionário.",
        nao_reconhecidas[["NOME_PROVA", "DESC_QUESTAO", "CODRESPOSTA", "TEXTO_ALTERNATIVA"]].drop_duplicates()))

    especificas = df[df["TIPO_PROVA"] != PROVA_INFRA]
    por_prova = especificas.groupby(["NOME_PROVA", "NOME_CURSO"])["ID_RESPONDENTE"].nunique().rename("questionarios")
    por_prova = por_prova.reset_index()
    principal = por_prova.loc[por_prova.groupby("NOME_PROVA")["questionarios"].idxmax(), ["NOME_PROVA", "NOME_CURSO"]]
    principal = principal.rename(columns={"NOME_CURSO": "curso_da_prova"})
    outros = por_prova.merge(principal, on="NOME_PROVA").query("NOME_CURSO != curso_da_prova")
    resultado.append(Checagem(
        "Prova de um curso respondida por aluno de outro curso", int(outros["questionarios"].sum()),
        "O aluno está matriculado em um curso, mas respondeu a prova de outro (disciplina cursada em outro curso "
        "ou aluno com duas matrículas). Nos gráficos 'por curso', essas respostas contam no curso do aluno.",
        outros.rename(columns={"NOME_CURSO": "curso_do_aluno"}), gravidade="aviso"))

    qtd = df.groupby(["CODPROVA", "ID_RESPONDENTE"]).size().rename("questoes").reset_index()
    esperado = qtd.groupby("CODPROVA")["questoes"].agg(lambda s: s.mode().iloc[0]).rename("esperado")
    qtd = qtd.merge(esperado, on="CODPROVA")
    incompletos = qtd[qtd["questoes"] < qtd["esperado"]]
    resultado.append(Checagem(
        "Questionários com menos questões que o normal da prova", len(incompletos),
        "Pode ser questionário interrompido ou questão adicionada depois do início da aplicação.",
        incompletos, gravidade="aviso"))
    return resultado


def investigar_curso(df: pd.DataFrame, curso: str) -> dict[str, pd.DataFrame]:
    c = df[df["NOME_CURSO"] == curso]
    tabelas = {
        "Questionários por prova, período e matrícula": (
            c.groupby(["AVALIACAO", "NOME_PROVA", "PERIODO_PROVA", "CODPERLET", "STATUS_MATRICULA"], dropna=False)
            ["ID_RESPONDENTE"].nunique().rename("questionarios").reset_index()),
        "Questionários por turma do aluno": (
            c.groupby(["AVALIACAO", "NOME_TURMA"], dropna=False)["ID_RESPONDENTE"].nunique()
            .rename("questionarios").reset_index()),
        "Avaliações docentes por professor, disciplina e turma": (
            c[c["TIPO_PROVA"] == PROVA_DOCENTE]
            .groupby(["NOME_PROFESSOR", "NOME_DISCIPLINA", "CODTURMA"], dropna=False)["ID_RESPONDENTE"].nunique()
            .rename("avaliacoes").reset_index()),
        "Classificação das respostas": (
            c["GRUPO"].fillna("Comentário / sem resposta").value_counts().rename("linhas").reset_index()),
    }
    return tabelas


def linha_do_tempo(df: pd.DataFrame) -> dict[str, pd.DataFrame] | None:
    if "DATA_RESPOSTA" not in df.columns or df["DATA_RESPOSTA"].isna().all():
        return None
    d = df.dropna(subset=["DATA_RESPOSTA"])
    por_questionario = d.groupby(["ID_RESPONDENTE", "AVALIACAO", "NOME_PROVA"])["DATA_RESPOSTA"].min().reset_index()
    por_questionario["DIA"] = por_questionario["DATA_RESPOSTA"].dt.date
    por_questionario["HORA"] = por_questionario["DATA_RESPOSTA"].dt.hour
    return {
        "por_dia": por_questionario.groupby(["DIA", "AVALIACAO"]).size().rename("questionarios").reset_index(),
        "por_hora": por_questionario.groupby("HORA").size().rename("questionarios").reset_index(),
        "por_prova": (d.groupby(["NOME_PROVA"])["DATA_RESPOSTA"].agg(primeira="min", ultima="max")
                      .reset_index().sort_values("primeira")),
    }
