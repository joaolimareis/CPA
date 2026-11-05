import pandas as pd
import pytest

from cpa.processing import processar


def reg(**campos):
    base = dict(TIPO_AVALIACAO="DOCENTE_DISCIPLINA", PERIODO_PROVA="2026/1", SEMESTRE="2026/1",
                CODPERLET="2026/1", CODCURSO="1", NOME_CURSO="Direito", CODTURMA="T1", NOME_TURMA="Turma",
                STATUS_MATRICULA="Cursando", ID_RESPONDENTE="1", CODPROVA="27", NOME_PROVA="Prova",
                CODPROF="P1", NOME_PROFESSOR="Prof", CODDISC="D1", NOME_DISCIPLINA="Disc", CODMATERIA="3",
                CODQUESTAO="1", DESC_QUESTAO="Questão", CODRESPOSTA="5", TEXTO_ALTERNATIVA="Concordo totalmente",
                COMENTARIO=None, TIPO_RESPOSTA="OBJETIVA")
    base.update(campos)
    return base


def test_remove_textos_informativos():
    df = processar([reg(), reg(CODRESPOSTA="ENTENDI!", TEXTO_ALTERNATIVA="."), reg(CODRESPOSTA="ENTENDI.")])
    assert len(df) == 1


def test_nota_global_vem_do_codigo_da_resposta():
    df = processar([reg(CODRESPOSTA="4", TEXTO_ALTERNATIVA=".")])
    assert df.loc[0, "ESCALA"] == "Nota global"
    assert df.loc[0, "NOTA"] == 4
    assert df.loc[0, "GRUPO"] == "Favorável"
    assert df.loc[0, "ALTERNATIVA"] == "Nota 4"


@pytest.mark.parametrize("texto,codigo,grupo", [
    ("Sim, sem reservas", "1", "Favorável"),
    ("Sim, com algumas ressalvas", "2", "Favorável"),
    ("Não", "3", "Desfavorável"),
])
def test_indicacao_nao_usa_o_codigo_como_nota(texto, codigo, grupo):
    df = processar([reg(CODRESPOSTA=codigo, TEXTO_ALTERNATIVA=texto)])
    assert df.loc[0, "GRUPO"] == grupo
    assert pd.isna(df.loc[0, "NOTA"])


def test_escala_de_concordancia_e_nao_se_aplica():
    df = processar([reg(TEXTO_ALTERNATIVA="Indiferente / Neutro", CODRESPOSTA="3"),
                    reg(TEXTO_ALTERNATIVA="Discordo parcialmente", CODRESPOSTA="2"),
                    reg(TEXTO_ALTERNATIVA="Não se aplica / Não tenho elementos para avaliar", CODRESPOSTA="NA")])
    assert df["GRUPO"].tolist() == ["Neutro", "Desfavorável", "Não se aplica"]
    assert df["VALIDA"].tolist() == [1, 1, 0]


def test_limpa_quebras_de_linha():
    df = processar([reg(TEXTO_ALTERNATIVA="\r\nConcordo totalmente", DESC_QUESTAO="Os canais mantêm\r\n os alunos")])
    assert df.loc[0, "GRUPO"] == "Favorável"
    assert df.loc[0, "DESC_QUESTAO"] == "Os canais mantêm os alunos"


def test_comentario_nao_entra_nos_percentuais():
    df = processar([reg(TIPO_RESPOSTA="DISSERTATIVA", COMENTARIO="Ótimo", CODRESPOSTA=None, TEXTO_ALTERNATIVA=None)])
    assert pd.isna(df.loc[0, "GRUPO"])
    assert df.loc[0, "VALIDA"] == 0
    assert df.loc[0, "E_COMENTARIO"] == 1


def test_cursos_excluidos():
    df = processar([reg(), reg(NOME_CURSO="Música")], cursos_excluidos=["Música"])
    assert df["NOME_CURSO"].tolist() == ["Direito"]


def test_coluna_faltando_gera_erro_claro():
    with pytest.raises(ValueError, match="COMENTARIO"):
        processar(pd.DataFrame([reg()]).drop(columns="COMENTARIO"))


def test_separa_curso_e_infraestrutura():
    df = processar([
        reg(TIPO_AVALIACAO="CURSO_INFRAESTRUTURA", CODPROVA="20", NOME_PROVA="Infraestrutura Institucional - Alunos"),
        reg(TIPO_AVALIACAO="CURSO_INFRAESTRUTURA", CODPROVA="33", NOME_PROVA="Direito - Especificidades do Curso"),
        reg(),
    ])
    assert df["TIPO_PROVA"].tolist() == ["INFRAESTRUTURA", "CURSO", "DOCENTE"]
    assert df["AVALIACAO"].tolist() == ["Infraestrutura", "Avaliação do Curso", "Docente e Disciplina"]


def test_separacao_por_codigo_da_prova():
    df = processar([reg(TIPO_AVALIACAO="CURSO_INFRAESTRUTURA", CODPROVA="99", NOME_PROVA="Questionário geral")],
                   provas_infra=["99"])
    assert df.loc[0, "TIPO_PROVA"] == "INFRAESTRUTURA"


def test_data_resposta_opcional_e_relatorio():
    rel = {}
    df = processar([reg(DATA_RESPOSTA="2026-04-10T14:22:31"), reg(CODRESPOSTA="ENTENDI!")], relatorio=rel)
    assert str(df.loc[0, "DATA_RESPOSTA"]) == "2026-04-10 14:22:31"
    assert rel == {"linhas_api": 2, "removidas_cursos_excluidos": 0, "removidas_textos_informativos": 1,
                   "removidas_questoes_anuladas": 0, "removidas_semestre_anterior": 0,
                   "removidas_avaliacoes_repetidas": 0, "linhas_finais": 1}


def test_cursos_permitidos_lista_fechada():
    df = processar([reg(), reg(NOME_CURSO="Capela"), reg(NOME_CURSO="Teologia")],
                   cursos_permitidos=["Direito", "Teologia"])
    assert sorted(df["NOME_CURSO"]) == ["Direito", "Teologia"]


def test_descarta_avaliacao_repetida_mantendo_a_mais_recente():
    rel = {}
    df = processar([reg(ID_RESPONDENTE="100", ULTIMA_AVALIACAO="200"),
                    reg(ID_RESPONDENTE="200", ULTIMA_AVALIACAO="200"),
                    reg(ID_RESPONDENTE="300", ULTIMA_AVALIACAO=None)], relatorio=rel)
    assert sorted(df["ID_RESPONDENTE"]) == ["200", "300"]
    assert rel["removidas_avaliacoes_repetidas"] == 1


def test_descarta_professor_de_semestre_anterior_e_guarda_motivo():
    rel, descartes = {}, []
    df = processar([reg(ID_RESPONDENTE="1", SEMESTRE_DISCIPLINA="2026/1T"),
                    reg(ID_RESPONDENTE="2", SEMESTRE_DISCIPLINA="2024/2"),
                    reg(ID_RESPONDENTE="3", SEMESTRE_DISCIPLINA="2026/1", ULTIMA_AVALIACAO="9"),
                    reg(ID_RESPONDENTE="4", SEMESTRE_DISCIPLINA=None, TIPO_AVALIACAO="CURSO_INFRAESTRUTURA")],
                   relatorio=rel, descartes=descartes)
    assert sorted(df["ID_RESPONDENTE"]) == ["1", "4"]
    assert rel["removidas_semestre_anterior"] == 1 and rel["removidas_avaliacoes_repetidas"] == 1
    motivos = dict(zip(descartes[0]["ID_RESPONDENTE"], descartes[0]["MOTIVO_DESCARTE"]))
    assert motivos == {"2": "Professor de semestre anterior", "3": "Avaliação repetida"}


def test_questoes_anuladas_so_na_prova_indicada():
    rel = {}
    df = processar([reg(CODPROVA="31", CODMATERIA="2", CODQUESTAO="15", TIPO_AVALIACAO="CURSO_INFRAESTRUTURA"),
                    reg(CODPROVA="33", CODMATERIA="2", CODQUESTAO="15", TIPO_AVALIACAO="CURSO_INFRAESTRUTURA"),
                    reg(CODPROVA="31", CODMATERIA="2", CODQUESTAO="11", TIPO_AVALIACAO="CURSO_INFRAESTRUTURA")],
                   relatorio=rel, questoes_anuladas=["31:2:15", "31:2:16"])
    assert sorted(df["CODPROVA"] + ":" + df["CODQUESTAO"]) == ["31:11", "33:15"]
    assert rel["removidas_questoes_anuladas"] == 1
