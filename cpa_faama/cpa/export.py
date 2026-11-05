"""Exportação dos resumos para Excel (somente dados agregados, sem identificação)."""
from __future__ import annotations

from io import BytesIO

import pandas as pd

NOMES_COLUNAS = {
    "NOME_CURSO": "Curso", "AVALIACAO": "Avaliação", "NOME_PROFESSOR": "Professor",
    "NOME_DISCIPLINA": "Disciplina", "NOME_PROVA": "Questionário", "DESC_QUESTAO": "Questão",
    "SEMESTRE": "Semestre", "questionarios": "Respondentes", "respostas_validas": "Respostas válidas",
    "pct_favoravel": "% Favorável", "pct_neutro": "% Neutro", "pct_desfavoravel": "% Desfavorável",
    "indice_confianca": "Índice de confiança", "nota_media": "Nota média", "nota_global": "Nota global",
    "pct_indicaria": "% Indicaria", "comentarios": "Comentários", "protegido": "Oculto por sigilo",
    "avaliacoes_insatisfeitas": "Alunos insatisfeitos", "avaliacoes_com_nota": "Alunos com resposta",
    "pct_insatisfeitos": "% Alunos insatisfeitos", "indice_alerta": "Índice de alerta",
    "recebidas": "Recebidas", "validas": "Aceitas", "semestre_anterior": "Descartadas: semestre anterior",
    "repetidas": "Descartadas: repetidas", "pct_validas": "% Aceitas", "pct_descartadas": "% Descartadas",
    "SEMESTRE_DISCIPLINA": "Semestre da disciplina", "avaliacoes": "Avaliações",
    "COMENTARIO": "Comentário", "posicao": "Posição", "CODTURMA": "Cód. turma", "NOME_TURMA": "Turma",
    "ALUNOS_MATRICULADOS": "Matriculados", "ALUNOS_RESPONDERAM": "Responderam",
    "ALUNOS_RESP_DOCENTE": "Responderam docente", "ALUNOS_RESP_INSTITUCIONAL": "Responderam institucional",
    "DOCENTE_ESPERADAS": "Avaliações docentes esperadas", "DOCENTE_RESPONDIDAS": "Avaliações docentes respondidas",
    "taxa_adesao": "% Adesão", "faltam": "Faltam p/ meta", "indice": "Índice", "taxa_docente": "% Docente",
    "taxa_institucional": "% Institucional", "completude": "% Completude docente",
}
REMOVER = {"favoraveis", "neutras", "desfavoraveis"}


def para_excel(planilhas: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as escritor:
        for nome, df in planilhas.items():
            tabela = df.drop(columns=[c for c in df.columns if c in REMOVER]).rename(columns=NOMES_COLUNAS)
            tabela.to_excel(escritor, sheet_name=nome[:31], index=False)
            folha = escritor.sheets[nome[:31]]
            for i, coluna in enumerate(tabela.columns, start=1):
                largura = min(60, max(12, int(tabela[coluna].astype(str).str.len().quantile(0.9) or 0) + 2, len(coluna) + 2))
                folha.column_dimensions[folha.cell(1, i).column_letter].width = largura
                if str(coluna).startswith("%") or coluna in ("Índice de confiança", "Índice", "Índice de alerta"):
                    for celula in folha.iter_rows(min_row=2, min_col=i, max_col=i):
                        celula[0].number_format = "0.0%"
    return buffer.getvalue()
