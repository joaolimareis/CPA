"""Relatório em Excel por curso, para as coordenações: todas as dimensões de cada professor/disciplina,
avaliação do curso, infraestrutura, comentários e participação por turma."""
from __future__ import annotations

import math
from datetime import date
from io import BytesIO

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from cpa import metrics, participacao
from cpa.processing import PROVA_CURSO, PROVA_DOCENTE, PROVA_INFRA

F = "Arial"
AZUL = "003B6F"
CAB = Font(name=F, bold=True, color="FFFFFF", size=10)
FUNDO = PatternFill("solid", fgColor=AZUL)
TEXTO = Font(name=F, size=10)
CINZA = Font(name=F, size=10, color="808080", italic=True)
PCT, NOTA = "0.0%", "0.00"


def _v(x, casas=None):
    if x is None or (isinstance(x, float) and np.isnan(x)) or pd.isna(x):
        return None
    if casas is None:
        return int(x)
    return round(float(x), casas)


def _aba(wb, nome, cab, linhas, larguras, formatos=None, nome_tabela=None):
    ws = wb.create_sheet(nome[:31])
    for j, (c, w) in enumerate(zip(cab, larguras), start=1):
        cel = ws.cell(1, j, c)
        cel.font, cel.fill = CAB, FUNDO
        cel.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[1].height = 48
    for i, lin in enumerate(linhas, start=2):
        for j, v in enumerate(lin, start=1):
            cel = ws.cell(i, j, v)
            cel.font = TEXTO
            cel.alignment = Alignment(vertical="top", wrap_text=isinstance(v, str) and len(v) > 35)
            if formatos and formatos.get(j):
                cel.number_format = formatos[j]
    if linhas:
        t = Table(displayName=(nome_tabela or "T" + "".join(ch for ch in nome if ch.isalnum()))[:250],
                  ref=f"A1:{get_column_letter(len(cab))}{len(linhas) + 1}")
        t.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
        ws.add_table(t)
    else:
        ws.cell(2, 1, "Sem dados neste semestre.").font = CINZA
    ws.freeze_panes = "A2"
    return ws


def _faltam(df, meta):
    necessario = (df["ALUNOS_MATRICULADOS"] * meta).apply(lambda v: math.ceil(round(v, 6)))
    return (necessario - df["ALUNOS_RESPONDERAM"]).clip(lower=0).astype(int)


def gerar(dados: pd.DataFrame, comentarios: pd.DataFrame, part: pd.DataFrame | None, curso: str, semestre: str,
          minimo: int, meta: float = 0.6) -> bytes:
    """`dados` = base tratada do curso no semestre; `comentarios` = saída de moderacao.preparar_comentarios
    para os mesmos dados; `part` = participação do curso no semestre (ou None)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Leia-me"
    ws.column_dimensions["A"].width = 115
    textos = [
        (f"Avaliação Institucional · {curso} · {semestre}", True, 14),
        (f"Relatório da CPA para a coordenação do curso. Gerado em {date.today():%d/%m/%Y} a partir do TOTVS RM.", False, 10),
        ("", False, 10), ("Abas", True, 11),
        ("• Resumo: participação e resultado de cada avaliação.", False, 10),
        ("• Docentes (dimensões): cada professor em cada disciplina, com o % favorável de cada questão avaliada.", False, 10),
        ("• Docentes por questão: as mesmas informações em lista, com respostas favoráveis, neutras e desfavoráveis.", False, 10),
        ("• Comentários docentes: o que os alunos escreveram sobre cada professor e disciplina.", False, 10),
        ("• Avaliação do curso e Infraestrutura: resultado por questão.", False, 10),
        ("• Comentários do curso: comentários sobre o curso e a infraestrutura.", False, 10),
        ("• Participação por turma: quantos alunos de cada turma responderam.", False, 10),
        ("", False, 10), ("Como ler", True, 11),
        ("• Favorável = concordo totalmente ou parcialmente, nota 4 ou 5, ou \"sim\" para indicar o professor. "
         "Neutro = indiferente ou nota 3. Desfavorável = discordo, nota 1 ou 2, ou \"não\". "
         "\"Não se aplica\" fica fora do cálculo.", False, 10),
        ("• % Favorável = respostas favoráveis ÷ respostas válidas. Nota global = média da nota de 1 a 5 dada ao docente.", False, 10),
        ("• Alunos insatisfeitos = alunos com mais respostas desfavoráveis do que favoráveis.", False, 10),
        ("", False, 10), ("Sigilo", True, 11),
        (f"• As respostas são anônimas. Professor/disciplina com menos de {minimo} respondentes mostra só o número "
         "de respondentes, e seus comentários não são exibidos. Os comentários passaram por moderação.", False, 10),
        ("• Este relatório é de uso da coordenação. Não repasse comentários que permitam identificar um aluno.", False, 10),
    ]
    for i, (t, negrito, tam) in enumerate(textos, start=1):
        cel = ws.cell(i, 1, t)
        cel.font = Font(name=F, bold=negrito, size=tam, color=AZUL if negrito else "000000")
        cel.alignment = Alignment(wrap_text=True)

    doc = dados[dados["TIPO_PROVA"] == PROVA_DOCENTE]
    cur = dados[dados["TIPO_PROVA"] == PROVA_CURSO]
    inf = dados[dados["TIPO_PROVA"] == PROVA_INFRA]

    # ---------- Resumo ----------
    linhas = []
    if part is not None and not part.empty:
        g = participacao.ranking(part.assign(_t="T"), ["_t"]).iloc[0]
        linhas.append(["Participação", "Alunos ativos", _v(g["ALUNOS_MATRICULADOS"]), None])
        linhas.append(["Participação", "Alunos que responderam", _v(g["ALUNOS_RESPONDERAM"]), None])
        linhas.append(["Participação", "Adesão", None, _v(g["taxa_adesao"], 4)])
        linhas.append(["Participação", "Completude docente", None, _v(g["completude"], 4)])
    for nome, bloco in (("Docente e Disciplina", doc), ("Avaliação do Curso", cur), ("Infraestrutura", inf)):
        if bloco.empty:
            continue
        ind = metrics.indicadores(bloco)
        linhas += [[nome, "Questionários respondidos", ind.questionarios, None],
                   [nome, "% Favorável", None, _v(ind.pct_favoravel, 4)],
                   [nome, "% Neutro", None, _v(ind.pct_neutro, 4)],
                   [nome, "% Desfavorável", None, _v(ind.pct_desfavoravel, 4)],
                   [nome, "Nota média (1 a 5)", _v(ind.nota_media, 2), None]]
        if nome == "Docente e Disciplina":
            linhas += [[nome, "Nota global do docente (1 a 5)", _v(ind.nota_global, 2), None],
                       [nome, "% Indicaria o docente", None, _v(ind.pct_indicaria, 4)]]
    _aba(wb, "Resumo", ["Avaliação", "Indicador", "Valor", "Percentual"], linhas, [24, 34, 12, 12],
         {3: "0.##", 4: PCT}, "Resumo")

    # ---------- Docentes (dimensões) ----------
    if not doc.empty:
        base = metrics.resumo_por(doc, ["NOME_PROFESSOR", "NOME_DISCIPLINA"], minimo)
        # Ordem do questionário: afirmações (escala de concordância) primeiro, depois nota global e indicação
        ordem_q = (doc[doc["VALIDA"] == 1]
                   .assign(_tipo=lambda x: x["ESCALA"].map({"Concordância": 0, "Nota global": 1, "Indicação": 2}).fillna(3),
                           _cod=lambda x: pd.to_numeric(x["CODQUESTAO"], errors="coerce"))
                   .groupby("DESC_QUESTAO")[["_tipo", "_cod"]].min().sort_values(["_tipo", "_cod"]))
        questoes = ordem_q.index.tolist()
        por_q = metrics.resumo_por(doc, ["NOME_PROFESSOR", "NOME_DISCIPLINA", "DESC_QUESTAO"])
        mapa = por_q.set_index(["NOME_PROFESSOR", "NOME_DISCIPLINA", "DESC_QUESTAO"])["pct_favoravel"]
        cab = ["Professor", "Disciplina", "Respondentes", "% Favorável geral", "Nota global (1 a 5)", "% Indicaria",
               "Alunos insatisfeitos"] + questoes + ["Observação"]
        linhas = []
        for r in base.sort_values(["NOME_PROFESSOR", "NOME_DISCIPLINA"]).itertuples():
            ok = not r.protegido
            lin = [r.NOME_PROFESSOR, r.NOME_DISCIPLINA, _v(r.questionarios),
                   _v(r.pct_favoravel, 4) if ok else None, _v(r.nota_global, 2) if ok else None,
                   _v(r.pct_indicaria, 4) if ok else None, _v(r.avaliacoes_insatisfeitas) if ok else None]
            lin += [_v(mapa.get((r.NOME_PROFESSOR, r.NOME_DISCIPLINA, q)), 4) if ok else None for q in questoes]
            lin.append("" if ok else f"Menos de {minimo} respondentes (sigilo)")
            linhas.append(lin)
        formatos = {4: PCT, 5: NOTA, 6: PCT}
        formatos.update({j: PCT for j in range(8, 8 + len(questoes))})
        _aba(wb, "Docentes (dimensões)", cab, linhas, [30, 34, 12, 12, 11, 11, 12] + [16] * len(questoes) + [30],
             formatos, "DocentesDimensoes")

        # ---------- Docentes por questão ----------
        protegidos = set(base.loc[base["protegido"], ["NOME_PROFESSOR", "NOME_DISCIPLINA"]].itertuples(index=False, name=None))
        linhas = [[r.NOME_PROFESSOR, r.NOME_DISCIPLINA, r.DESC_QUESTAO, _v(r.respostas_validas), _v(r.favoraveis),
                   _v(r.neutras), _v(r.desfavoraveis), _v(r.pct_favoravel, 4), _v(r.pct_desfavoravel, 4)]
                  for r in por_q.sort_values(["NOME_PROFESSOR", "NOME_DISCIPLINA", "DESC_QUESTAO"]).itertuples()
                  if (r.NOME_PROFESSOR, r.NOME_DISCIPLINA) not in protegidos and r.respostas_validas > 0]
        _aba(wb, "Docentes por questão", ["Professor", "Disciplina", "Questão", "Respostas válidas", "Favoráveis",
                                          "Neutras", "Desfavoráveis", "% Favorável", "% Desfavorável"], linhas,
             [28, 32, 60, 11, 11, 10, 12, 11, 12], {8: PCT, 9: PCT}, "DocentesQuestao")
    else:
        _aba(wb, "Docentes (dimensões)", ["Professor"], [], [30])

    # ---------- comentários ----------
    vis = comentarios[comentarios["VISIVEL"]] if not comentarios.empty else comentarios
    cd = vis[vis["TIPO_PROVA"] == PROVA_DOCENTE] if not vis.empty else vis
    linhas = []
    if not cd.empty:
        agrup = (cd.groupby(["NOME_PROFESSOR", "NOME_DISCIPLINA", "COMENTARIO_EXIBIDO"], sort=False).size()
                 .rename("vezes").reset_index().sort_values(["NOME_PROFESSOR", "NOME_DISCIPLINA"]))
        linhas = [[r.NOME_PROFESSOR, r.NOME_DISCIPLINA, r.COMENTARIO_EXIBIDO, int(r.vezes)] for r in agrup.itertuples()]
    _aba(wb, "Comentários docentes", ["Professor", "Disciplina", "Comentário", "Vezes"], linhas, [28, 32, 90, 8],
         nome_tabela="ComentariosDocentes")

    for nome, bloco in (("Avaliação do curso", cur), ("Infraestrutura", inf)):
        n = bloco["ID_RESPONDENTE"].nunique() if not bloco.empty else 0
        linhas = []
        if n >= minimo:
            q = metrics.resumo_por(bloco, ["DESC_QUESTAO"]).dropna(subset=["pct_favoravel"])
            linhas = [[r.DESC_QUESTAO, _v(r.respostas_validas), _v(r.pct_favoravel, 4), _v(r.pct_neutro, 4),
                       _v(r.pct_desfavoravel, 4), _v(r.nota_media, 2)] for r in q.itertuples()]
        ws = _aba(wb, nome, ["Questão", "Respostas válidas", "% Favorável", "% Neutro", "% Desfavorável", "Nota média"],
                  linhas, [70, 11, 11, 10, 12, 11], {3: PCT, 4: PCT, 5: PCT, 6: NOTA}, nome.replace(" ", ""))
        if 0 < n < minimo:
            ws.cell(3, 1, f"{n} respondente(s): menos de {minimo}, resultado não detalhado (sigilo).").font = CINZA

    cc = vis[vis["TIPO_PROVA"].isin([PROVA_CURSO, PROVA_INFRA])] if not vis.empty else vis
    linhas = [[r.AVALIACAO, r.COMENTARIO_EXIBIDO] for r in cc.itertuples()] if not cc.empty else []
    _aba(wb, "Comentários do curso", ["Avaliação", "Comentário"], linhas, [24, 100], nome_tabela="ComentariosCurso")

    # ---------- participação por turma ----------
    linhas = []
    if part is not None and not part.empty:
        t = participacao.ranking(part, ["NOME_TURMA"], ordenar="taxa_adesao")
        t = t.assign(faltam=_faltam(t, meta))
        linhas = [[r.NOME_TURMA, _v(r.ALUNOS_MATRICULADOS), _v(r.ALUNOS_RESPONDERAM), _v(r.taxa_adesao, 4),
                   _v(r.completude, 4), int(r.faltam)] for r in t.itertuples()]
    _aba(wb, "Participação por turma", ["Turma", "Alunos ativos", "Responderam", "Adesão", "Completude docente",
                                        f"Faltavam p/ meta de {meta:.0%}"], linhas, [36, 12, 12, 10, 12, 14],
         {4: PCT, 5: PCT}, "ParticipacaoTurma")

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
