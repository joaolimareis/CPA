"""Relatório da CPA em PDF: visão consolidada para direção e avaliadores externos (sem nomes)."""
from __future__ import annotations

from datetime import date
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,  # noqa: E402
                                Table, TableStyle)

from cpa import metrics, participacao  # noqa: E402
from cpa.config import RAIZ  # noqa: E402
from cpa.processing import PROVA_CURSO, PROVA_DOCENTE, PROVA_INFRA  # noqa: E402

AZUL = colors.HexColor("#003B6F")
TINTA = colors.HexColor("#13263B")
CINZA = colors.HexColor("#5B6B7D")
LINHA = colors.HexColor("#DCE3EC")
FUNDO = colors.HexColor("#F2F5F9")

_base = getSampleStyleSheet()
ESTILO = {
    "titulo": ParagraphStyle("titulo", parent=_base["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27,
                             textColor=AZUL, alignment=TA_CENTER),
    "subtitulo": ParagraphStyle("subtitulo", parent=_base["Normal"], fontSize=12, leading=16, textColor=CINZA,
                                alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", parent=_base["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=19,
                         textColor=AZUL, spaceBefore=6, spaceAfter=8),
    "h2": ParagraphStyle("h2", parent=_base["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=15,
                         textColor=TINTA, spaceBefore=10, spaceAfter=5),
    "texto": ParagraphStyle("texto", parent=_base["Normal"], fontSize=9.5, leading=13.5, textColor=TINTA),
    "nota": ParagraphStyle("nota", parent=_base["Normal"], fontSize=8, leading=11, textColor=CINZA),
    "celula": ParagraphStyle("celula", parent=_base["Normal"], fontSize=8.3, leading=10.5, textColor=TINTA),
    "cab": ParagraphStyle("cab", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=8.3, leading=10.5,
                          textColor=colors.white),
}


def _pct(v) -> str:
    return "—" if v is None or pd.isna(v) else f"{v * 100:.1f}%".replace(".", ",")


def _num(v, casas=0) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _tabela(cabecalho: list[str], linhas: list[list], larguras: list[float]) -> Table:
    dados = [[Paragraph(c, ESTILO["cab"]) for c in cabecalho]]
    dados += [[Paragraph(str(c), ESTILO["celula"]) for c in lin] for lin in linhas]
    t = Table(dados, colWidths=[w * cm for w in larguras], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FUNDO]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINHA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _grafico_barras(rotulos: list[str], valores: list[float], titulo_x: str) -> Image:
    fig, ax = plt.subplots(figsize=(7.2, 0.42 * len(rotulos) + 0.8), dpi=200)
    ordem = sorted(zip(valores, rotulos))
    vs, rs = [v for v, _ in ordem], [r for _, r in ordem]
    ax.barh(rs, vs, color="#003B6F", height=0.6)
    for i, v in enumerate(vs):
        ax.text(v + 0.01, i, f"{v * 100:.1f}%".replace(".", ","), va="center", fontsize=8, color="#13263B")
    ax.set_xlim(0, 1.1)
    ax.set_xlabel(titulo_x, fontsize=8, color="#5B6B7D")
    ax.tick_params(labelsize=8, colors="#13263B")
    ax.xaxis.set_visible(False)
    for lado in ("top", "right", "bottom"):
        ax.spines[lado].set_visible(False)
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return Image(buffer, width=16 * cm, height=16 * cm * fig.get_figheight() / fig.get_figwidth())


def _rodape(semestre: str):
    def desenhar(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(CINZA)
        canvas.drawString(2 * cm, 1.2 * cm, f"CPA FAAMA - Relatório de Autoavaliação Institucional {semestre}")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
        canvas.restoreState()
    return desenhar


def gerar(df: pd.DataFrame, part: pd.DataFrame | None, semestre: str, minimo: int, instituicao: str = "FAAMA") -> bytes:
    """`df` = base tratada de um semestre; `part` = participação do mesmo semestre (ou None)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                            bottomMargin=2 * cm, title=f"Relatório CPA {semestre}", author=f"CPA {instituicao}")
    h = []

    # ---------- capa ----------
    logo = RAIZ / "assets" / "logo.png"
    h.append(Spacer(1, 4 * cm))
    if logo.exists():
        img = Image(str(logo), width=3.2 * cm, height=3.2 * cm)
        img.hAlign = "CENTER"
        h += [img, Spacer(1, 1 * cm)]
    h += [Paragraph("Relatório de Autoavaliação Institucional", ESTILO["titulo"]), Spacer(1, 0.3 * cm),
          Paragraph(f"Resultados do semestre {semestre}", ESTILO["subtitulo"]), Spacer(1, 0.2 * cm),
          Paragraph(f"Comissão Própria de Avaliação · {instituicao}", ESTILO["subtitulo"]), Spacer(1, 6 * cm),
          Paragraph(f"Gerado em {date.today():%d/%m/%Y} a partir dos dados do TOTVS RM. Respostas anônimas; "
                    f"grupos com menos de {minimo} respondentes não são detalhados.", ESTILO["nota"]),
          PageBreak()]

    # ---------- 1. metodologia ----------
    h += [Paragraph("1. Metodologia", ESTILO["h1"]), Paragraph(
        "A autoavaliação segue as diretrizes do SINAES (Lei nº 10.861/2004). Os alunos respondem, pelo portal "
        "acadêmico, à avaliação docente e da disciplina (uma para cada professor do semestre), à avaliação do curso "
        "e à avaliação de infraestrutura e atendimento. Respostas \"concordo totalmente/parcialmente\", notas 4 e 5 "
        "e \"sim\" são favoráveis; \"indiferente\" e nota 3 são neutras; \"discordo\", notas 1 e 2 e \"não\" são "
        "desfavoráveis; \"não se aplica\" fica fora do cálculo. Entram apenas avaliações de professores de "
        "disciplinas do próprio semestre, e avaliações repetidas contam uma única vez.", ESTILO["texto"])]

    # ---------- 2. participação ----------
    h.append(Paragraph("2. Participação", ESTILO["h1"]))
    if part is not None and not part.empty:
        rk = participacao.ranking(part, ["NOME_CURSO"])
        total = participacao.ranking(part.assign(_t="Total"), ["_t"]).iloc[0]
        h.append(Paragraph(
            f"Responderam {_num(total['ALUNOS_RESPONDERAM'])} dos {_num(total['ALUNOS_MATRICULADOS'])} alunos ativos, "
            f"uma adesão de {_pct(total['taxa_adesao'])}. A completude da avaliação docente (avaliações de "
            f"professores realizadas sobre as possíveis) foi de {_pct(total['completude'])}.", ESTILO["texto"]))
        h.append(Spacer(1, 0.3 * cm))
        linhas = [[r.NOME_CURSO, _num(r.ALUNOS_MATRICULADOS), _num(r.ALUNOS_RESPONDERAM), _pct(r.taxa_adesao),
                   _pct(r.completude)] for r in rk.sort_values("taxa_adesao", ascending=False).itertuples()]
        h.append(_tabela(["Curso", "Alunos ativos", "Responderam", "Adesão", "Completude docente"], linhas,
                         [6.4, 2.6, 2.6, 2.2, 3.2]))
        h.append(Spacer(1, 0.3 * cm))
        h.append(_grafico_barras(rk["NOME_CURSO"].tolist(), rk["taxa_adesao"].fillna(0).tolist(), "Adesão"))
    else:
        h.append(Paragraph("Dados de participação não disponíveis para este semestre.", ESTILO["texto"]))

    # ---------- 3. resultado geral ----------
    h += [PageBreak(), Paragraph("3. Resultado geral por avaliação", ESTILO["h1"])]
    tipos = metrics.resumo_por(df, ["AVALIACAO"]).sort_values("AVALIACAO", ascending=False)
    h.append(_tabela(["Avaliação", "Questionários", "% Favorável", "% Neutro", "% Desfavorável", "Nota média"],
                     [[r.AVALIACAO, _num(r.questionarios), _pct(r.pct_favoravel), _pct(r.pct_neutro),
                       _pct(r.pct_desfavoravel), _num(r.nota_media, 2)] for r in tipos.itertuples()],
                     [4.6, 2.6, 2.4, 2.2, 2.6, 2.6]))
    h.append(Paragraph("Questionários: na avaliação docente, cada professor avaliado por um aluno conta um "
                       "questionário.", ESTILO["nota"]))

    # ---------- 4. docente por curso ----------
    doc_df = df[df["TIPO_PROVA"] == PROVA_DOCENTE]
    h.append(Paragraph("4. Avaliação docente e da disciplina, por curso", ESTILO["h1"]))
    if not doc_df.empty:
        por_curso = metrics.resumo_por(doc_df, ["NOME_CURSO"], minimo).sort_values("NOME_CURSO")
        h.append(_tabela(["Curso", "Avaliações", "% Favorável", "Nota global (1 a 5)", "% Indicaria o professor"],
                         [[r.NOME_CURSO, _num(r.questionarios), _pct(r.pct_favoravel), _num(r.nota_global, 2),
                           _pct(r.pct_indicaria)] for r in por_curso.itertuples()], [6.2, 2.4, 2.6, 3.0, 2.8]))
        validos = por_curso.dropna(subset=["pct_favoravel"])
        if not validos.empty:
            h.append(Spacer(1, 0.3 * cm))
            h.append(_grafico_barras(validos["NOME_CURSO"].tolist(), validos["pct_favoravel"].tolist(), "% favorável"))
        por_questao = metrics.resumo_por(doc_df, ["DESC_QUESTAO"]).dropna(subset=["pct_favoravel"])
        if not por_questao.empty:
            h.append(Paragraph("Resultado por questão (todos os cursos)", ESTILO["h2"]))
            h.append(_tabela(["Questão", "Respostas", "% Favorável", "% Desfavorável"],
                             [[r.DESC_QUESTAO, _num(r.respostas_validas), _pct(r.pct_favoravel),
                               _pct(r.pct_desfavoravel)] for r in por_questao.sort_values("pct_favoravel").itertuples()],
                             [10.2, 2.0, 2.4, 2.4]))
    else:
        h.append(Paragraph("Sem respostas neste semestre.", ESTILO["texto"]))

    # ---------- 5. curso ----------
    curso_df = df[df["TIPO_PROVA"] == PROVA_CURSO]
    h += [PageBreak(), Paragraph("5. Avaliação do curso", ESTILO["h1"])]
    if curso_df.empty:
        h.append(Paragraph("Sem respostas neste semestre.", ESTILO["texto"]))
    for curso in sorted(curso_df["NOME_CURSO"].dropna().unique()):
        bloco = curso_df[curso_df["NOME_CURSO"] == curso]
        n = bloco["ID_RESPONDENTE"].nunique()
        partes = [Paragraph(f"{curso} ({_num(n)} respondentes)", ESTILO["h2"])]
        if n < minimo:
            partes.append(Paragraph(f"Menos de {minimo} respondentes: resultado não detalhado.", ESTILO["nota"]))
        else:
            q = metrics.resumo_por(bloco, ["DESC_QUESTAO"]).dropna(subset=["pct_favoravel"])
            partes.append(_tabela(["Questão", "% Favorável", "% Neutro", "% Desfavorável"],
                                  [[r.DESC_QUESTAO, _pct(r.pct_favoravel), _pct(r.pct_neutro), _pct(r.pct_desfavoravel)]
                                   for r in q.itertuples()], [10.4, 2.2, 2.0, 2.4]))
        h.append(KeepTogether(partes))

    # ---------- 6. infraestrutura ----------
    infra_df = df[df["TIPO_PROVA"] == PROVA_INFRA]
    h.append(Paragraph("6. Infraestrutura e atendimento", ESTILO["h1"]))
    if infra_df.empty:
        h.append(Paragraph("Sem respostas neste semestre.", ESTILO["texto"]))
    else:
        q = metrics.resumo_por(infra_df, ["DESC_QUESTAO"]).dropna(subset=["pct_favoravel"])
        h.append(Paragraph(f"{_num(infra_df['ID_RESPONDENTE'].nunique())} respondentes.", ESTILO["texto"]))
        h.append(_tabela(["Questão", "% Favorável", "% Neutro", "% Desfavorável"],
                         [[r.DESC_QUESTAO, _pct(r.pct_favoravel), _pct(r.pct_neutro), _pct(r.pct_desfavoravel)]
                          for r in q.sort_values("pct_favoravel").itertuples()], [10.4, 2.2, 2.0, 2.4]))

    # ---------- 7. pontos de atenção ----------
    h.append(Paragraph("7. Pontos de atenção", ESTILO["h1"]))
    h.append(Paragraph(f"Itens com 15% ou mais de respostas desfavoráveis e pelo menos {minimo} respondentes.",
                       ESTILO["texto"]))
    alerta_curso = metrics.pontos_de_atencao(curso_df, ["NOME_CURSO", "DESC_QUESTAO"], minimo, 0.15)
    alerta_infra = metrics.pontos_de_atencao(infra_df, ["DESC_QUESTAO"], minimo, 0.15)
    alerta_doc = metrics.pontos_de_atencao(doc_df, ["NOME_PROFESSOR", "NOME_DISCIPLINA"], minimo, 0.15)
    linhas = [["Curso: " + str(r.NOME_CURSO), r.DESC_QUESTAO, _pct(r.pct_desfavoravel)] for r in alerta_curso.itertuples()]
    linhas += [["Infraestrutura", r.DESC_QUESTAO, _pct(r.pct_desfavoravel)] for r in alerta_infra.itertuples()]
    if linhas:
        h.append(_tabela(["Avaliação", "Questão", "% Desfavorável"], linhas, [4.0, 10.4, 2.6]))
    else:
        h.append(Paragraph("Nenhuma questão do curso ou de infraestrutura atingiu o critério.", ESTILO["texto"]))
    h.append(Spacer(1, 0.2 * cm))
    h.append(Paragraph(f"Avaliação docente: {len(alerta_doc)} combinação(ões) de professor e disciplina atingiram o "
                       "critério. O detalhamento por professor é tratado pela CPA com as coordenações, sem divulgação "
                       "nominal.", ESTILO["texto"]))

    doc.build(h, onFirstPage=lambda c, d: None, onLaterPages=_rodape(semestre))
    return buffer.getvalue()
