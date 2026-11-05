"""PDF de participação por turma, um curso por página, para enviar aos coordenadores."""
from __future__ import annotations

import math
from datetime import date
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer  # noqa: E402

from cpa import participacao  # noqa: E402
from cpa.charts import cor_meta  # noqa: E402
from cpa.config import RAIZ  # noqa: E402
from cpa.relatorio_pdf import ESTILO, _num, _pct, _tabela  # noqa: E402


def faltam_para_meta(df: pd.DataFrame, meta: float) -> pd.Series:
    necessario = (df["ALUNOS_MATRICULADOS"] * meta).apply(lambda v: math.ceil(round(v, 6)))
    return (necessario - df["ALUNOS_RESPONDERAM"]).clip(lower=0).astype(int)


def _termometro_png(rotulos, valores, respondidos, matriculados, meta, vertical) -> Image:
    n = len(rotulos)
    if vertical:
        fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=200)
        pos = range(n)
        ax.bar(pos, [1] * n, color="#E6EBF1", width=0.55)
        ax.bar(pos, valores, color=[cor_meta(v, meta) for v in valores], width=0.55)
        for i, (v, r, m) in enumerate(zip(valores, respondidos, matriculados)):
            ax.text(i, v + 0.03, f"{v * 100:.0f}%\n{r} de {m}".replace(".", ","), ha="center", va="bottom",
                    fontsize=7.5, color="#13263B")
        ax.axhline(meta, ls="--", lw=1, color="#13263B")
        ax.text(n - 0.5, meta + 0.02, f"meta {meta * 100:.0f}%", ha="right", fontsize=7.5)
        ax.set_xticks(list(pos), [r if len(r) < 18 else r[:16] + "…" for r in rotulos], fontsize=7.5, rotation=0)
        ax.set_ylim(0, 1.25)
        ax.yaxis.set_visible(False)
    else:
        fig, ax = plt.subplots(figsize=(7.2, 0.42 * n + 0.9), dpi=200)
        pos = range(n)
        ax.barh(pos, [1] * n, color="#E6EBF1", height=0.55)
        ax.barh(pos, valores, color=[cor_meta(v, meta) for v in valores], height=0.55)
        for i, (v, r, m) in enumerate(zip(valores, respondidos, matriculados)):
            ax.text(1.02, i, f"{v * 100:.0f}%  ({r} de {m})".replace(".", ","), va="center", fontsize=7.5,
                    color="#13263B")
        ax.axvline(meta, ls="--", lw=1, color="#13263B")
        ax.text(meta, n - 0.35, f"meta {meta * 100:.0f}%", ha="center", fontsize=7.5)
        ax.set_yticks(list(pos), [r if len(r) < 42 else r[:40] + "…" for r in rotulos], fontsize=7.5)
        ax.set_xlim(0, 1.35)
        ax.xaxis.set_visible(False)
    for lado in ("top", "right", "left", "bottom"):
        ax.spines[lado].set_visible(False)
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return Image(buffer, width=16.5 * cm, height=16.5 * cm * fig.get_figheight() / fig.get_figwidth())


def _cabecalho(titulo: str, subtitulo: str) -> list:
    partes = []
    logo = RAIZ / "assets" / "logo.png"
    if logo.exists():
        img = Image(str(logo), width=1.4 * cm, height=1.4 * cm)
        img.hAlign = "LEFT"
        partes.append(img)
    partes += [Paragraph(titulo, ESTILO["h1"]), Paragraph(subtitulo, ESTILO["nota"]), Spacer(1, 0.3 * cm)]
    return partes


def gerar(turmas: pd.DataFrame, todos: pd.DataFrame, semestre: str, cursos: list[str], meta: float) -> bytes:
    """`turmas` = turmas válidas do semestre (sem residuais); `todos` = todas as linhas do semestre (para os totais)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, title=f"Participação por turma {semestre}", author="CPA FAAMA")
    hoje = f"{date.today():%d/%m/%Y}"
    h = []
    if len(cursos) > 1:
        rk = participacao.ranking(todos[todos["NOME_CURSO"].isin(cursos)], ["NOME_CURSO"])
        rk = rk.sort_values("taxa_adesao", ascending=False)
        h += _cabecalho(f"Termômetro de participação dos cursos · {semestre}",
                        f"Avaliação Institucional CPA FAAMA. Situação em {hoje}. Meta de adesão: {_pct(meta)}.")
        h.append(_termometro_png(rk["NOME_CURSO"].tolist(), rk["taxa_adesao"].fillna(0).tolist(),
                                 rk["ALUNOS_RESPONDERAM"].astype(int).tolist(),
                                 rk["ALUNOS_MATRICULADOS"].astype(int).tolist(), meta, vertical=True))
        h.append(Spacer(1, 0.3 * cm))
        h.append(_tabela(["Curso", "Alunos ativos", "Responderam", "Adesão", "Faltam p/ meta"],
                         [[r.NOME_CURSO, _num(r.ALUNOS_MATRICULADOS), _num(r.ALUNOS_RESPONDERAM), _pct(r.taxa_adesao),
                           _num(f)] for r, f in zip(rk.itertuples(), faltam_para_meta(rk, meta))],
                         [6.6, 2.6, 2.6, 2.2, 3.0]))
        h.append(PageBreak())
    for i, curso in enumerate(cursos):
        t = turmas[turmas["NOME_CURSO"] == curso]
        tot = participacao.ranking(todos[todos["NOME_CURSO"] == curso].assign(_t="T"), ["_t"])
        h += _cabecalho(f"Participação por turma · {curso}",
                        f"Avaliação Institucional CPA FAAMA, semestre {semestre}. Situação em {hoje}. "
                        f"Meta de adesão: {_pct(meta)}.")
        if not tot.empty:
            g = tot.iloc[0]
            h.append(Paragraph(f"No curso, responderam <b>{_num(g['ALUNOS_RESPONDERAM'])} de "
                               f"{_num(g['ALUNOS_MATRICULADOS'])}</b> alunos (adesão de <b>{_pct(g['taxa_adesao'])}</b>).",
                               ESTILO["texto"]))
            h.append(Spacer(1, 0.2 * cm))
        rt = participacao.ranking(t, ["NOME_TURMA"]) if not t.empty else t
        if rt.empty:
            h.append(Paragraph("Nenhuma turma com avaliação aberta neste semestre.", ESTILO["texto"]))
        else:
            rt = rt.sort_values("taxa_adesao", ascending=False)
            h.append(_termometro_png(rt["NOME_TURMA"].tolist()[::-1], rt["taxa_adesao"].fillna(0).tolist()[::-1],
                                     rt["ALUNOS_RESPONDERAM"].astype(int).tolist()[::-1],
                                     rt["ALUNOS_MATRICULADOS"].astype(int).tolist()[::-1], meta, vertical=False))
            h.append(Spacer(1, 0.25 * cm))
            h.append(_tabela(["Turma", "Alunos ativos", "Responderam", "Adesão", "Faltam p/ meta"],
                             [[r.NOME_TURMA, _num(r.ALUNOS_MATRICULADOS), _num(r.ALUNOS_RESPONDERAM),
                               _pct(r.taxa_adesao), _num(f)] for r, f in zip(rt.itertuples(), faltam_para_meta(rt, meta))],
                             [6.6, 2.6, 2.6, 2.2, 3.0]))
        h.append(Spacer(1, 0.3 * cm))
        h.append(Paragraph("Verde: atingiu a meta. Amarelo: passou da metade da meta. Vermelho: abaixo da metade. "
                           "Turmas com menos de 5 alunos ou sem avaliação aberta não aparecem.", ESTILO["nota"]))
        if i < len(cursos) - 1:
            h.append(PageBreak())
    doc.build(h)
    return buffer.getvalue()
