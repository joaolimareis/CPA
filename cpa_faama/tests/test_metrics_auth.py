import math

from cpa import auth, demo, metrics, moderacao
from cpa.processing import processar


def base():
    return processar(demo.gerar(semente=1))


def test_wilson_penaliza_amostra_pequena():
    pequeno, grande = metrics.wilson_inferior([3, 95], [3, 100])
    assert pequeno < grande


def test_indicadores_somam_100():
    ind = metrics.indicadores(base())
    assert math.isclose(ind.pct_favoravel + ind.pct_neutro + ind.pct_desfavoravel, 1.0)


def test_resumo_oculta_grupos_pequenos():
    df = base()
    r = metrics.resumo_por(df, ["NOME_PROFESSOR"], min_respondentes=10_000)
    assert r["protegido"].all() and r["pct_favoravel"].isna().all()


def test_comentarios_respeitam_minimo():
    df = base()
    assert not moderacao.preparar_comentarios(df, 10_000, moderacao.PADRAO)["VISIVEL"].any()
    assert moderacao.preparar_comentarios(df, 1, moderacao.PADRAO)["VISIVEL"].any()


def test_escopo_por_perfil():
    df = base()
    coord = auth.Usuario("c", "C", "coordenador", cursos=("Direito",))
    prof = auth.Usuario("p", "P", "professor", codprof="P100")
    assert set(auth.aplicar_escopo(df, coord)["NOME_CURSO"]) == {"Direito"}
    visto = auth.aplicar_escopo(df, prof)
    assert set(visto["CODPROF"]) == {"P100"} and set(visto["TIPO_AVALIACAO"]) == {"DOCENTE_DISCIPLINA"}
    assert auth.aplicar_escopo(df, None).empty


def test_autenticacao():
    usuarios = {"cpa": {"nome": "CPA", "perfil": "admin", "senha_hash": auth.gerar_hash("segredo123")}}
    assert auth.autenticar("CPA", "segredo123", usuarios).perfil == "admin"
    assert auth.autenticar("cpa", "errada", usuarios) is None
    assert auth.autenticar("ninguem", "x", usuarios) is None


def test_ranking_participacao_equilibra_tamanho():
    import pandas as pd
    from cpa import participacao
    df = participacao.processar(pd.DataFrame([
        dict(SEMESTRE="2026/1", CODPERLET="2026/1", NOME_CURSO="A", CODTURMA="P", NOME_TURMA="Pequena",
             ALUNOS_MATRICULADOS=3, ALUNOS_RESPONDERAM=3, ALUNOS_RESP_DOCENTE=3, ALUNOS_RESP_INSTITUCIONAL=3,
             DOCENTE_ESPERADAS=15, DOCENTE_RESPONDIDAS=15),
        dict(SEMESTRE="2026/1", CODPERLET="2026/1", NOME_CURSO="A", CODTURMA="M", NOME_TURMA="Média",
             ALUNOS_MATRICULADOS=50, ALUNOS_RESPONDERAM=45, ALUNOS_RESP_DOCENTE=45, ALUNOS_RESP_INSTITUCIONAL=40,
             DOCENTE_ESPERADAS=250, DOCENTE_RESPONDIDAS=300),
        dict(SEMESTRE="2026/1", CODPERLET="2026/1", NOME_CURSO="B", CODTURMA="G", NOME_TURMA="Grande",
             ALUNOS_MATRICULADOS=200, ALUNOS_RESPONDERAM=80, ALUNOS_RESP_DOCENTE=80, ALUNOS_RESP_INSTITUCIONAL=70,
             DOCENTE_ESPERADAS=1000, DOCENTE_RESPONDIDAS=400),
    ]))
    r = participacao.ranking(df, ["NOME_TURMA"])
    assert r["NOME_TURMA"].tolist() == ["Média", "Pequena", "Grande"]
    media = r.set_index("NOME_TURMA").loc["Média"]
    assert media["inconsistente"] and pd.isna(media["completude"])


def test_alunos_insatisfeitos_contam_pessoas():
    import pandas as pd
    from cpa.processing import processar
    linhas = []
    for i, alts in enumerate([["Discordo totalmente"] * 4, ["Concordo totalmente"] * 4,
                              ["Concordo totalmente", "Concordo totalmente", "Discordo totalmente", "Concordo parcialmente"]]):
        for q, alt in enumerate(alts):
            linhas.append(dict(TIPO_AVALIACAO="DOCENTE_DISCIPLINA", PERIODO_PROVA="2026/1", SEMESTRE="2026/1",
                               CODPERLET="2026/1", CODCURSO="1", NOME_CURSO="Direito", CODTURMA="T", NOME_TURMA="T",
                               STATUS_MATRICULA="Cursando", ID_RESPONDENTE=str(i), CODPROVA="27", NOME_PROVA="P",
                               CODPROF="P1", NOME_PROFESSOR="Prof", CODDISC="D", NOME_DISCIPLINA="Disc",
                               CODMATERIA="3", CODQUESTAO=str(q), DESC_QUESTAO=f"Q{q}", CODRESPOSTA="1",
                               TEXTO_ALTERNATIVA=alt, COMENTARIO=None, TIPO_RESPOSTA="OBJETIVA"))
    r = metrics.resumo_por(processar(linhas), ["NOME_PROFESSOR"]).iloc[0]
    assert r["avaliacoes_insatisfeitas"] == 1 and r["avaliacoes_com_nota"] == 3
    assert abs(r["pct_insatisfeitos"] - 1 / 3) < 1e-9
    assert abs(r["pct_desfavoravel"] - 5 / 12) < 1e-9


def test_avaliador_externo_com_validade():
    from datetime import date, timedelta
    hoje = date.today()
    usuarios = {
        "mec": {"nome": "MEC", "perfil": "avaliador", "senha_hash": auth.gerar_hash("senha12345"),
                "valido_ate": (hoje + timedelta(days=3)).isoformat()},
        "mec.velho": {"nome": "MEC", "perfil": "avaliador", "senha_hash": auth.gerar_hash("senha12345"),
                      "valido_ate": (hoje - timedelta(days=1)).isoformat()},
    }
    u = auth.autenticar("mec", "senha12345", usuarios)
    assert u is not None and u.perfil == "avaliador" and not u.expirado
    assert auth.autenticar("mec.velho", "senha12345", usuarios) is None
    df = base()
    assert len(auth.aplicar_escopo(df, u)) == len(df)


def test_relatorio_pdf_gera_documento():
    from cpa import relatorio_pdf, participacao
    df = base()
    sem = df[df["SEMESTRE"] == "2026/1"]
    part = participacao.processar(participacao.gerar_demo())
    pdf = relatorio_pdf.gerar(sem, part[part["SEMESTRE"] == "2026/1"], "2026/1", 5)
    assert pdf[:4] == b"%PDF" and len(pdf) > 20_000
