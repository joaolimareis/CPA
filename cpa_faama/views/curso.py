from cpa import pagina_avaliacao
from cpa.processing import PROVA_CURSO

pagina_avaliacao.render(PROVA_CURSO, "Avaliação do Curso",
                        "Coordenação, estágios, práticas e laboratórios: questionário específico de cada curso",
                        chave="curso", filtro_questionario=True)
