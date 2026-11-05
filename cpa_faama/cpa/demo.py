"""Dados fictícios no mesmo formato da API, para testar o sistema sem acessar o TOTVS."""
from __future__ import annotations

import random

CURSOS = ["Direito", "Enfermagem", "Psicologia", "Pedagogia", "Análise e Desenvolvimento de Sistemas"]
QUESTOES_DOCENTE = [
    "O(a) professor(a) domina o conteúdo e explica bem?",
    "O(a) professor(a) tira dúvidas e oferece devolutiva sobre o seu desempenho?",
    "O(a) professor(a) é ético(a) e trata todos os alunos de forma justa?",
    "O(a) professor(a) cumpriu o conteúdo e os prazos combinados?",
    "As regras de avaliação foram claras e justas?",
    "A disciplina ajuda na sua formação profissional?",
]
QUESTOES_CURSO = [
    "A coordenação do curso responde de forma adequada aos alunos?",
    "As atividades práticas e os estágios estão de acordo com as normas do curso?",
    "Os laboratórios atendem bem às necessidades das aulas práticas?",
]
QUESTOES_INFRA = [
    "As salas de aula e seus recursos audiovisuais atendem adequadamente às aulas?",
    "O acervo da biblioteca disponibiliza a bibliografia necessária?",
    "A rede Wi-Fi e os sistemas acadêmicos funcionam de modo estável?",
    "Os espaços de alimentação atendem adequadamente às suas necessidades?",
]
ESCALA = ["Concordo totalmente", "Concordo parcialmente", "Indiferente / Neutro",
          "Discordo parcialmente", "Discordo totalmente",
          "Não se aplica / Não tenho elementos para avaliar"]
CODIGOS = ["5", "4", "3", "2", "1", "NA"]
COMENTARIOS = [
    "Excelente professor, explica com clareza e paciência.",
    "Poderia dar mais exemplos práticos durante as aulas.",
    "As avaliações poderiam ter critérios mais claros.",
    "Muito atencioso com a turma, sempre disponível para dúvidas.",
    "O conteúdo é bom, mas o ritmo das aulas é muito rápido.",
    "O Wi-Fi cai com frequência nas salas do bloco B.",
    "A biblioteca precisa de mais exemplares dos livros básicos.",
    "A coordenação responde rápido e resolve os problemas.",
]


def _linha(**campos) -> dict:
    base = {c: None for c in (
        "TIPO_AVALIACAO PERIODO_PROVA SEMESTRE CODPERLET CODCURSO NOME_CURSO CODTURMA NOME_TURMA "
        "STATUS_MATRICULA ID_RESPONDENTE CODPROVA NOME_PROVA CODPROF NOME_PROFESSOR CODDISC "
        "NOME_DISCIPLINA CODMATERIA CODQUESTAO DESC_QUESTAO CODRESPOSTA TEXTO_ALTERNATIVA "
        "COMENTARIO TIPO_RESPOSTA ULTIMA_AVALIACAO SEMESTRE_DISCIPLINA").split()}
    base.update(campos)
    return base


def _resposta(rng: random.Random, qualidade: float) -> tuple[str, str]:
    pesos = [0.55 * qualidade, 0.25, 0.07, 0.05 / qualidade, 0.03 / qualidade, 0.05]
    i = rng.choices(range(6), weights=pesos)[0]
    return CODIGOS[i], ESCALA[i]


def gerar(semente: int = 42) -> list[dict]:
    rng = random.Random(semente)
    registros: list[dict] = []
    id_seq = 1000
    professores = [(f"P{100 + i}", f"Professor(a) Exemplo {i + 1:02d}", rng.uniform(0.7, 1.4)) for i in range(24)]
    for semestre, fator in (("2025/2", 0.95), ("2026/1", 1.0)):
        for c, curso in enumerate(CURSOS):
            profs = professores[c * 4:(c * 4) + 6]
            alunos = rng.randint(25, 60)
            comum = dict(PERIODO_PROVA=semestre, SEMESTRE=semestre, CODPERLET=semestre,
                         CODCURSO=str(c + 1), NOME_CURSO=curso, CODTURMA=f"T{c + 1}A",
                         NOME_TURMA=f"{curso} - Turma A")
            for _ in range(alunos):
                status = "Cancelado" if rng.random() < 0.03 else "Cursando"
                # Avaliação docente: um questionário por professor avaliado
                for codprof, nome, qualidade in rng.sample(profs, k=rng.randint(2, len(profs))):
                    id_seq += 1
                    disc = f"Disciplina {codprof[-2:]}"
                    # parte dos alunos avalia professores de disciplinas de semestres anteriores (como no RM real)
                    sem_disc = semestre if rng.random() > 0.12 else rng.choice(["2024/2", "2025/1", "2023 - 2S"])
                    doc = dict(comum, TIPO_AVALIACAO="DOCENTE_DISCIPLINA", STATUS_MATRICULA=status,
                               ID_RESPONDENTE=str(id_seq), CODPROVA="27",
                               NOME_PROVA=f"{curso} - Avaliação Docente e Disciplina",
                               CODPROF=codprof, NOME_PROFESSOR=nome, CODDISC=f"D{codprof}",
                               NOME_DISCIPLINA=disc, CODMATERIA="3", SEMESTRE_DISCIPLINA=sem_disc,
                               ULTIMA_AVALIACAO=str(id_seq))
                    registros.append(_linha(**doc, CODQUESTAO="10", DESC_QUESTAO="Prezado(a) discente...",
                                            CODRESPOSTA="ENTENDI!", TEXTO_ALTERNATIVA=".", TIPO_RESPOSTA="OBJETIVA"))
                    for q, texto in enumerate(QUESTOES_DOCENTE, start=1):
                        cod, alt = _resposta(rng, qualidade * fator)
                        registros.append(_linha(**doc, CODQUESTAO=str(q), DESC_QUESTAO=texto,
                                                CODRESPOSTA=cod, TEXTO_ALTERNATIVA=alt, TIPO_RESPOSTA="OBJETIVA"))
                    nota = str(max(1, min(5, round(rng.gauss(3.6 + qualidade, 0.7)))))
                    registros.append(_linha(**doc, CODQUESTAO="8", TEXTO_ALTERNATIVA=".", CODRESPOSTA=nota,
                                            DESC_QUESTAO="De forma global, atribua uma nota ao desempenho do(a) docente:",
                                            TIPO_RESPOSTA="OBJETIVA"))
                    ind = rng.choices(["1", "2", "3"], weights=[0.7 * qualidade, 0.2, 0.1 / qualidade])[0]
                    registros.append(_linha(**doc, CODQUESTAO="9", CODRESPOSTA=ind,
                                            TEXTO_ALTERNATIVA={"1": "Sim, sem reservas", "2": "Sim, com algumas ressalvas", "3": "Não"}[ind],
                                            DESC_QUESTAO="Você indicaria este(a) docente para colegas?",
                                            TIPO_RESPOSTA="OBJETIVA"))
                    tem_coment = rng.random() < 0.3
                    registros.append(_linha(**doc, CODQUESTAO="11",
                                            DESC_QUESTAO="Comentários sobre o(a) docente/disciplina (opcional)",
                                            COMENTARIO=rng.choice(COMENTARIOS[:5]) if tem_coment else None,
                                            TIPO_RESPOSTA="DISSERTATIVA" if tem_coment else "SEM RESPOSTA"))
                # Avaliação do curso e da infraestrutura: questionários diferentes (parte dos alunos responde)
                provas = (("33", f"{curso} - Especificidades do Curso", QUESTOES_CURSO, COMENTARIOS[7:], 0.95),
                          ("20", "Infraestrutura Institucional - Alunos", QUESTOES_INFRA, COMENTARIOS[5:7], 0.85))
                for codprova, nome_prova, questoes, coments, qualidade in provas:
                    if rng.random() >= 0.4:
                        continue
                    id_seq += 1
                    cur = dict(comum, TIPO_AVALIACAO="CURSO_INFRAESTRUTURA", STATUS_MATRICULA=status,
                               ID_RESPONDENTE=str(id_seq), CODPROVA=codprova, NOME_PROVA=nome_prova, CODMATERIA="1")
                    for q, texto in enumerate(questoes, start=1):
                        cod, alt = _resposta(rng, qualidade * fator)
                        registros.append(_linha(**cur, CODQUESTAO=str(q), DESC_QUESTAO=texto,
                                                CODRESPOSTA=cod, TEXTO_ALTERNATIVA=alt, TIPO_RESPOSTA="OBJETIVA"))
                    tem_coment = rng.random() < 0.35
                    texto_coment = rng.choice(coments + [".", "Ótimo"]) if tem_coment else None
                    registros.append(_linha(**cur, CODQUESTAO="9", DESC_QUESTAO="Comentários e sugestões (opcional)",
                                            COMENTARIO=texto_coment,
                                            TIPO_RESPOSTA="DISSERTATIVA" if tem_coment else "SEM RESPOSTA"))
    return registros
