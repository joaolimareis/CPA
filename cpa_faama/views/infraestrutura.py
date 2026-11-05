from cpa import pagina_avaliacao
from cpa.processing import PROVA_INFRA

pagina_avaliacao.render(PROVA_INFRA, "Infraestrutura Institucional",
                        "Salas, biblioteca, Wi-Fi, alimentação, atendimento e comunicação: questionário comum a todos os cursos",
                        chave="infra", filtro_questionario=False)
