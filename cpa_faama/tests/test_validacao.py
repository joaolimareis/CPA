from cpa import demo, validacao
from cpa.processing import processar


def test_resumo_soma_aceitas_e_descartadas():
    d = []
    df = processar(demo.gerar(), descartes=d)
    docentes = df[df["TIPO_PROVA"] == "DOCENTE"]
    r = validacao.resumo(docentes, d[0], ["NOME_CURSO"])
    assert (r["recebidas"] == r["validas"] + r["semestre_anterior"] + r["repetidas"]).all()
    assert r["semestre_anterior"].sum() > 0
    assert not validacao.professores_anteriores(d[0]).empty


def test_relatorio_docente_gera_excel_com_abas():
    from io import BytesIO
    import openpyxl
    from cpa import relatorio_docente
    df = processar(demo.gerar())
    doc = df[(df["TIPO_PROVA"] == "DOCENTE") & (df["SEMESTRE"] == "2026/1")]
    wb = openpyxl.load_workbook(BytesIO(relatorio_docente.gerar(doc, ["2026/1"], 5)))
    assert wb.sheetnames == ["Leia-me", "Resumo por Curso", "Professor x Disciplina", "Por Professor", "Por Questão"]
    assert wb["Professor x Disciplina"].max_row > 2


def test_pdf_participacao_por_turma():
    from cpa import participacao, relatorio_participacao
    p = participacao.processar(participacao.gerar_demo())
    sem = p[p["SEMESTRE"] == "2026/1"]
    cursos = sorted(sem["NOME_CURSO"].unique())
    pdf = relatorio_participacao.gerar(sem, sem, "2026/1", cursos, 0.6)
    assert pdf[:4] == b"%PDF"
    f = relatorio_participacao.faltam_para_meta(sem.assign(ALUNOS_MATRICULADOS=10, ALUNOS_RESPONDERAM=4), 0.6)
    assert (f == 2).all()
