import streamlit as st

from cpa import ui
from cpa.config import get_settings

ui.aplicar_estilo()
s = get_settings()
ui.cabecalho("Metodologia", "Como a avaliação é aplicada, como os dados são tratados e como o sigilo é garantido", None)

cursos = ", ".join(s.cursos_permitidos) if s.cursos_permitidos else "todos os cursos da consulta"
st.markdown(f"""
### O instrumento
A Autoavaliação Institucional é conduzida pela Comissão Própria de Avaliação (CPA), em consonância com o
Sistema Nacional de Avaliação da Educação Superior (SINAES, Lei nº 10.861/2004). O aluno responde, pelo
portal do TOTVS RM, três instrumentos:

- **Avaliação docente e da disciplina:** um questionário para cada professor e disciplina que o aluno cursa
  no semestre, com a escala de concordância, a nota global de 1 a 5 e a indicação do professor.
- **Avaliação do curso:** coordenação, estágios, práticas e estrutura específica de cada curso.
- **Infraestrutura e atendimento:** salas, biblioteca, recursos digitais, alimentação, atendimento e
  comunicação, comuns a todos os cursos.

### Escala e cálculo
| Resposta | Grupo |
|---|---|
| Concordo totalmente ou parcialmente; nota 4 ou 5; "sim" para indicar o professor | Favorável |
| Indiferente / neutro; nota 3 | Neutro |
| Discordo parcialmente ou totalmente; nota 1 ou 2; "não" | Desfavorável |
| Não se aplica | Fora do cálculo |

O percentual favorável é o número de respostas favoráveis dividido pelo número de respostas válidas.

### Quem entra na análise
- Alunos dos cursos de graduação: {cursos}.
- Somente avaliações de professores de disciplinas do próprio semestre.
- Se o aluno avaliou o mesmo professor e disciplina mais de uma vez, vale a avaliação mais recente.
- Questões aplicadas por engano em um questionário são desconsideradas.

### Participação
- **Adesão:** alunos que responderam pelo menos um questionário válido, divididos pelos alunos ativos no
  semestre (situação "Cursando", ou "Concluído" após o encerramento do semestre).
- **Ranking por curso:** ordenado pela adesão.
- **Ranking por turma:** ordenado pelo índice de participação, a adesão ajustada pelo tamanho da turma
  (limite inferior de Wilson, 95%), para que turmas pequenas não fiquem à frente por acaso.
- **Completude docente:** avaliações de professores realizadas, divididas pelas que os alunos poderiam fazer.

### Sigilo
As respostas são anônimas: nenhuma tela ou relatório mostra nome ou matrícula de aluno. Resultados de grupos
com menos de **{s.min_respondentes} respondentes** não são exibidos separadamente (continuam somados nos
totais), e os comentários passam por moderação antes de serem exibidos.

### Origem dos dados
Os dados são lidos diretamente do TOTVS RM, sem digitação manual, e atualizados automaticamente a cada
{s.cache_minutos} minutos. A CPA confere a consistência dos dados em páginas de validação e auditoria.
""")
