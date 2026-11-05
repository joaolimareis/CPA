import pandas as pd

from cpa import moderacao
from cpa.processing import processar

CFG = {**moderacao.PADRAO, "ocultos_manualmente": []}


def test_sem_conteudo():
    for texto in [".", "....", "-", "ok", "N/A", "Nada.", "nada a declarar"]:
        assert moderacao.classificar(texto, CFG)[0] == moderacao.SEM_CONTEUDO, texto
    assert moderacao.classificar("Ótima", CFG)[0] == moderacao.APROVADO


def test_palavrao_ignora_acento_e_maiuscula():
    assert moderacao.classificar("Que DESGRAÇA de aula", CFG)[0] == moderacao.PALAVRAO
    assert moderacao.classificar("Professor é um idiota", CFG)[0] == moderacao.PALAVRAO


def test_nao_confunde_palavras_parecidas():
    for texto in ["O computador do laboratório", "A disputa foi justa", "Viaduto perto da faculdade",
                  "Curso excelente", "Escuta os alunos"]:
        assert moderacao.classificar(texto, CFG)[0] == moderacao.APROVADO, texto


def test_mascarar_preserva_o_resto():
    cfg = {**CFG, "modo": "mascarar"}
    situacao, exibido = moderacao.classificar("Aula boa, mas que porra de horário", cfg)
    assert situacao == moderacao.MASCARADO
    assert exibido == "Aula boa, mas que ***** de horário"


def test_oculto_manual_e_preparar():
    linhas = [dict(TIPO_AVALIACAO="DOCENTE_DISCIPLINA", PERIODO_PROVA="2026/1", SEMESTRE="2026/1", CODPERLET="2026/1",
                   CODCURSO="1", NOME_CURSO="Direito", CODTURMA="T", NOME_TURMA="T", STATUS_MATRICULA="Cursando",
                   ID_RESPONDENTE=str(i), CODPROVA="27", NOME_PROVA="P", CODPROF="P1", NOME_PROFESSOR="Prof",
                   CODDISC="D", NOME_DISCIPLINA="Disc", CODMATERIA="3", CODQUESTAO="10", DESC_QUESTAO="Comentários",
                   CODRESPOSTA=None, TEXTO_ALTERNATIVA=None, COMENTARIO=texto, TIPO_RESPOSTA="DISSERTATIVA")
              for i, texto in enumerate(["Muito bom", ".", "Explica bem", "Ótimo professor", "Gosto das aulas"])]
    df = processar(linhas)
    alvo = moderacao.chave("2", "3", "10")
    cfg = {**CFG, "ocultos_manualmente": [moderacao.chave("0", "3", "10")]}
    out = moderacao.preparar_comentarios(df, 5, cfg)
    assert out["VISIVEL"].sum() == 3
    assert set(out.loc[~out["VISIVEL"], "MODERACAO"]) == {moderacao.MANUAL, moderacao.SEM_CONTEUDO}
    assert alvo in set(out["CHAVE"])
    assert isinstance(out, pd.DataFrame)
