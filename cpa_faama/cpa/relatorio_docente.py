"""Relatório em Excel da avaliação docente (mesmo formato da planilha enviada à CPA)."""
from __future__ import annotations

from datetime import date
from io import BytesIO

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from cpa import metrics

F = "Arial"
AZUL = "003B6F"
CAB = Font(name=F, bold=True, color="FFFFFF", size=10)
FUNDO = PatternFill("solid", fgColor=AZUL)
TEXTO = Font(name=F, size=10)
CINZA = Font(name=F, size=10, color="808080", italic=True)


def _tabela(ws, cab, linhas, larguras, nome):
    for j, (c, w) in enumerate(zip(cab, larguras), start=1):
        cel = ws.cell(1, j, c)
        cel.font, cel.fill = CAB, FUNDO
        cel.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[1].height = 42
    for i, lin in enumerate(linhas, start=2):
        for j, v in enumerate(lin, start=1):
            if isinstance(v, float) and np.isnan(v):
                v = None
            cel = ws.cell(i, j, v)
            cel.font = TEXTO
            cel.alignment = Alignment(vertical="top", wrap_text=isinstance(v, str) and len(v) > 40)
    ultima = max(len(linhas) + 1, 2)
    t = Table(displayName=nome, ref=f"A1:{get_column_letter(len(cab))}{ultima}")
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(t)
    ws.freeze_panes = "A2"
    return ultima


def _formato(ws, colunas, ultima, fmt):
    for col in colunas:
        for i in range(2, ultima + 1):
            ws[f"{col}{i}"].number_format = fmt


def _v(x, casas=None):
    if x is None or pd.isna(x):
        return None
    return round(float(x), casas) if casas is not None else int(x)


def gerar(docente: pd.DataFrame, semestres: list[str], minimo: int) -> bytes:
    """`docente` = respostas válidas da avaliação docente já filtradas (semestre, curso, perfil)."""
    por_disc = metrics.resumo_por(docente, ["NOME_CURSO", "NOME_PROFESSOR", "NOME_DISCIPLINA"])
    prof = metrics.resumo_por(docente, ["NOME_PROFESSOR"])
    if not prof.empty:
        extra = docente.groupby("NOME_PROFESSOR").agg(
            cursos=("NOME_CURSO", lambda s: ", ".join(sorted(s.dropna().unique()))),
            disciplinas=("NOME_DISCIPLINA", "nunique")).reset_index()
        prof = prof.merge(extra, on="NOME_PROFESSOR")
    curso = metrics.resumo_por(docente, ["NOME_CURSO"])
    if not curso.empty:
        curso = curso.merge(docente.groupby("NOME_CURSO")["NOME_PROFESSOR"].nunique().rename("professores").reset_index(),
                            on="NOME_CURSO")
    q = metrics.resumo_por(docente, ["NOME_CURSO", "NOME_PROFESSOR", "NOME_DISCIPLINA", "DESC_QUESTAO"])
    if not q.empty:
        n = por_disc.set_index(["NOME_CURSO", "NOME_PROFESSOR", "NOME_DISCIPLINA"])["questionarios"]
        chave = q.set_index(["NOME_CURSO", "NOME_PROFESSOR", "NOME_DISCIPLINA"]).index
        q = q[(chave.map(n).to_numpy() >= minimo) & (q["respostas_validas"].to_numpy() > 0)]

    wb = Workbook()
    ws = wb.active
    ws.title = "Leia-me"
    ws.column_dimensions["A"].width = 110
    sem = ", ".join(semestres)
    textos = [
        (f"Avaliação Discente dos Professores por Disciplina · {sem}", True, 14),
        (f"Fonte: TOTVS RM (consulta da CPA). Gerado pelo Sistema CPA em {date.today():%d/%m/%Y}.", False, 10),
        ("", False, 10), ("Regras aplicadas", True, 11),
        ("• Só os cursos de graduação da CPA.", False, 10),
        ("• Só avaliações de professores de disciplinas do próprio semestre.", False, 10),
        ("• Avaliação repetida pelo mesmo aluno para o mesmo professor e disciplina: vale só a mais recente.", False, 10),
        (f"• Sigilo: professor/disciplina com menos de {minimo} respondentes mostra só o número de respondentes. "
         "Essas respostas continuam somadas nos totais por professor e por curso.", False, 10),
        ("• Nenhuma aba traz nome ou RA de aluno. Comentários não estão incluídos.", False, 10),
        ("", False, 10), ("Como ler as colunas", True, 11),
        ("• Respondentes: alunos que avaliaram o professor naquela disciplina.", False, 10),
        ("• Favorável = concordo totalmente/parcialmente, nota 4–5 ou \"sim\"; Neutro = indiferente ou nota 3; "
         "Desfavorável = discordo, nota 1–2 ou \"não\". Os percentuais são fórmulas sobre as respostas válidas.", False, 10),
        ("• Nota global (1 a 5): média da questão de nota ao desempenho do(a) docente.", False, 10),
        ("• % Indicaria: alunos que indicariam o professor (com ou sem ressalvas).", False, 10),
        ("• Alunos insatisfeitos: alunos com mais respostas desfavoráveis do que favoráveis.", False, 10),
    ]
    for i, (t, negrito, tam) in enumerate(textos, start=1):
        cel = ws.cell(i, 1, t)
        cel.font = Font(name=F, bold=negrito, size=tam, color=AZUL if negrito else "000000")
        cel.alignment = Alignment(wrap_text=True)

    def pct(k, num, den="E"):
        return f'=IF(OR($D{k}<{minimo},${den}{k}=0),"",{num}{k}/${den}{k})'

    # Resumo por curso
    ws = wb.create_sheet("Resumo por Curso")
    linhas = []
    for k, (_, r) in enumerate(curso.sort_values("NOME_CURSO").iterrows(), start=2):
        linhas.append([r.NOME_CURSO, _v(r.professores), _v(r.questionarios), _v(r.respostas_validas), _v(r.favoraveis),
                       _v(r.neutras), _v(r.desfavoraveis), f'=IF(D{k}=0,"",E{k}/D{k})', f'=IF(D{k}=0,"",F{k}/D{k})',
                       f'=IF(D{k}=0,"",G{k}/D{k})', _v(r.nota_global, 2), _v(r.pct_indicaria, 4)])
    if linhas:
        k = len(linhas) + 2
        linhas.append(["Total", None] + [f"=SUM({c}2:{c}{k - 1})" for c in "CDEFG"] +
                      [f'=IF(D{k}=0,"",E{k}/D{k})', f'=IF(D{k}=0,"",F{k}/D{k})', f'=IF(D{k}=0,"",G{k}/D{k})', None, None])
    ult = _tabela(ws, ["Curso", "Professores avaliados", "Avaliações (questionários)", "Respostas válidas", "Favoráveis",
                       "Neutras", "Desfavoráveis", "% Favorável", "% Neutro", "% Desfavorável", "Nota global (1 a 5)",
                       "% Indicaria"], linhas, [36, 12, 14, 12, 11, 10, 12, 11, 10, 12, 11, 10], "ResumoCurso")
    _formato(ws, "HIJL", ult, "0.0%")
    _formato(ws, "K", ult, "0.00")
    if linhas:
        for j in range(1, 13):
            ws.cell(ult, j).font = Font(name=F, size=10, bold=True)

    # Professor x Disciplina
    ws = wb.create_sheet("Professor x Disciplina")
    linhas = []
    for k, (_, r) in enumerate(por_disc.sort_values(["NOME_CURSO", "NOME_PROFESSOR", "NOME_DISCIPLINA"]).iterrows(), start=2):
        ok = r.questionarios >= minimo
        linhas.append([r.NOME_CURSO, r.NOME_PROFESSOR, r.NOME_DISCIPLINA, _v(r.questionarios)] +
                      ([_v(r.respostas_validas), _v(r.favoraveis), _v(r.neutras), _v(r.desfavoraveis)] if ok else [None] * 4) +
                      [pct(k, "F"), pct(k, "G"), pct(k, "H"),
                       _v(r.nota_global, 2) if ok else None, _v(r.pct_indicaria, 4) if ok else None,
                       _v(r.avaliacoes_insatisfeitas) if ok else None,
                       "" if ok else f"Menos de {minimo} respondentes (sigilo)"])
    ult = _tabela(ws, ["Curso", "Professor", "Disciplina", "Respondentes", "Respostas válidas", "Favoráveis", "Neutras",
                       "Desfavoráveis", "% Favorável", "% Neutro", "% Desfavorável", "Nota global (1 a 5)", "% Indicaria",
                       "Alunos insatisfeitos", "Observação"], linhas,
                  [22, 32, 40, 12, 11, 11, 10, 12, 11, 10, 12, 11, 10, 12, 30], "ProfessorDisciplina")
    _formato(ws, "IJKM", ult, "0.0%")
    _formato(ws, "L", ult, "0.00")
    for i in range(2, ult + 1):
        if ws[f"O{i}"].value:
            ws[f"O{i}"].font = CINZA

    # Por professor
    ws = wb.create_sheet("Por Professor")
    linhas = []
    for k, (_, r) in enumerate(prof.sort_values("NOME_PROFESSOR").iterrows(), start=2):
        ok = r.questionarios >= minimo
        linhas.append([r.NOME_PROFESSOR, r.cursos, _v(r.disciplinas), _v(r.questionarios)] +
                      ([_v(r.respostas_validas), _v(r.favoraveis), _v(r.neutras), _v(r.desfavoraveis)] if ok else [None] * 4) +
                      [pct(k, "F"), pct(k, "H"), _v(r.nota_global, 2) if ok else None,
                       _v(r.pct_indicaria, 4) if ok else None, _v(r.avaliacoes_insatisfeitas) if ok else None,
                       "" if ok else f"Menos de {minimo} respondentes (sigilo)"])
    ult = _tabela(ws, ["Professor", "Cursos", "Disciplinas", "Respondentes (avaliações)", "Respostas válidas", "Favoráveis",
                       "Neutras", "Desfavoráveis", "% Favorável", "% Desfavorável", "Nota global (1 a 5)", "% Indicaria",
                       "Alunos insatisfeitos", "Observação"], linhas,
                  [32, 26, 11, 13, 11, 11, 10, 12, 11, 12, 11, 10, 12, 30], "PorProfessor")
    _formato(ws, "IJL", ult, "0.0%")
    _formato(ws, "K", ult, "0.00")

    # Por questão
    ws = wb.create_sheet("Por Questão")
    linhas = []
    for k, (_, r) in enumerate(q.sort_values(["NOME_CURSO", "NOME_PROFESSOR", "NOME_DISCIPLINA", "DESC_QUESTAO"]).iterrows(),
                               start=2):
        linhas.append([r.NOME_CURSO, r.NOME_PROFESSOR, r.NOME_DISCIPLINA, r.DESC_QUESTAO, _v(r.respostas_validas),
                       _v(r.favoraveis), _v(r.neutras), _v(r.desfavoraveis), f'=IF(E{k}=0,"",F{k}/E{k})',
                       f'=IF(E{k}=0,"",H{k}/E{k})'])
    ult = _tabela(ws, ["Curso", "Professor", "Disciplina", "Questão", "Respostas válidas", "Favoráveis", "Neutras",
                       "Desfavoráveis", "% Favorável", "% Desfavorável"], linhas,
                  [22, 30, 34, 70, 11, 11, 10, 12, 11, 12], "PorQuestao")
    _formato(ws, "IJ", ult, "0.0%")

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
