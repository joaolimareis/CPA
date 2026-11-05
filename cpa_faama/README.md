# Sistema CPA · Avaliação Institucional

Sistema web interno que consome a consulta SQL da avaliação institucional pela API do TOTVS RM
e apresenta os resultados com controle de acesso por perfil e regras de sigilo.

## Novidades desta versão

- Identidade visual da FAAMA (logo, cores e tipografia) e página **Início** com a situação da avaliação.
- Perfil **avaliador externo** (ex.: visita do MEC), somente leitura e com data de validade.
- **Relatório da CPA em PDF**, página **Histórico** e página **Metodologia**.
- **Registro de acessos** e encerramento automático de sessão por inatividade.
- Guia de publicação em servidor com HTTPS: veja `DEPLOY.md`.

## O que ele faz além do relatório do Power BI

- **Acesso por perfil**: a CPA vê tudo; cada coordenador vê só os próprios cursos; cada professor
  vê só os próprios resultados, comparados com a média da instituição. O recorte é aplicado no
  servidor, antes de qualquer tela.
- **Ranking justo de professores**: ordenado por um índice de confiança (limite inferior de Wilson),
  que impede que um professor com 3 respostas (100%) fique à frente de outro com 100 respostas (95%).
- **Mapa de calor** professor × questão e curso × questão.
- **Pontos de atenção** automáticos, com limite ajustável de % desfavorável.
- **Avaliação do Curso e Infraestrutura separadas**, cada uma com sua página.
- **Comentários moderados**: remove textos sem conteúdo (como "."), filtra palavrões e permite que a CPA
  oculte comentários específicos. Busca por palavra e termos mais citados.
- **Ranking de participação** proporcional ao tamanho das turmas (taxa de adesão ajustada por Wilson e
  completude da avaliação docente), alimentado pela consulta `sql/participacao.sql`.
- **Auditoria dos dados**: checagens automáticas, totais para conferir com o TOTVS, linha do tempo das
  respostas e investigação por curso, com um pacote de consultas SQL em `sql/auditoria_totvs.sql`.
- **Comparação com o semestre anterior** nos indicadores e gráfico de evolução.
- **Exportação para Excel** dos resumos (só dados agregados).
- **Funciona mesmo com a API fora do ar**, usando a última cópia salva.

## Estrutura

```
cpa_faama/
├── app.py                  # entrada: login e menu conforme o perfil
├── cpa/                    # lógica (sem telas, exceto ui.py e a parte de sessão do auth.py)
│   ├── config.py           # leitura do .env
│   ├── totvs_client.py     # cliente da API REST do TOTVS (RealizaConsulta)
│   ├── processing.py       # tratamento dos dados: mesmas regras do Power Query
│   ├── metrics.py          # indicadores, resumos, sigilo, índice de confiança
│   ├── repository.py       # busca, cópia local (parquet) e plano B se a API cair
│   ├── moderacao.py        # filtro de comentários (sem conteúdo, palavrões, ocultos pela CPA)
│   ├── auditoria.py        # checagens de consistência e conferência com o TOTVS
│   ├── participacao.py     # ranking de participação por turma e curso
│   ├── pagina_avaliacao.py # página padrão usada por Curso e Infraestrutura
│   ├── auth.py             # login (bcrypt), perfis e recorte dos dados
│   ├── charts.py           # gráficos Plotly
│   ├── export.py           # exportação para Excel
│   ├── ui.py               # componentes de tela compartilhados
│   └── demo.py             # dados fictícios para testar sem o TOTVS
├── views/                  # uma página por arquivo
│   ├── visao_geral.py
│   ├── docentes.py
│   ├── curso.py            # Avaliação do Curso (questionário específico de cada curso)
│   ├── infraestrutura.py   # Infraestrutura (questionário comum a todos)
│   ├── comentarios.py
│   ├── atencao.py
│   ├── meu_resultado.py    # exclusiva do perfil professor
│   ├── ranking.py          # Ranking de Participação (CPA e coordenadores)
│   ├── auditoria.py        # exclusiva da CPA
│   └── admin.py            # exclusiva da CPA
├── sql/
│   ├── auditoria_totvs.sql       # consultas para conferir os dados direto no RM
│   ├── participacao.sql          # consulta de participação (cadastrar no RM)
│   ├── diagnostico_matricula.sql # confirma respostas atribuídas ao curso errado
│   └── consulta_cpa_v10.sql       # consulta da CPA (FAAMACPA.6) com a escolha de matrícula corrigida
├── scripts/criar_usuario.py
├── config/usuarios.example.yaml
├── config/moderacao.yaml   # regras do filtro de comentários (criado no primeiro uso)
├── tests/                  # pytest
├── data/                   # cópia local dos dados (não versionar)
├── .streamlit/config.toml  # tema e segurança do Streamlit
├── .env.example
├── requirements.txt
└── Dockerfile
```

## Como rodar

Requer Python 3.11 ou superior.

```bash
# 1. Ambiente virtual e dependências
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Configuração
copy .env.example .env          # Linux/Mac: cp .env.example .env
#    edite o .env com a URL, o usuário e a senha da API do TOTVS

# 3. Primeiro usuário (a CPA)
python scripts/criar_usuario.py cpa --nome "Comissão Própria de Avaliação" --perfil admin

# 4. Subir o sistema
streamlit run app.py
```

Acesse http://localhost:8501.

Para testar sem acessar o TOTVS, deixe `TOTVS_BASE_URL` vazio no `.env`: o sistema sobe em
**modo demonstração**, com dados fictícios.

## Usuários e perfis

| Perfil | Vê | Como criar |
|---|---|---|
| `admin` | Tudo, mais a página de Administração | `--perfil admin` |
| `coordenador` | Só os cursos informados | `--perfil coordenador --cursos "Direito;Psicologia"` |
| `professor` | Só as próprias avaliações (página Meu Resultado) | `--perfil professor --codprof 01234` |
| `avaliador` | Visões consolidadas, sem nomes de professores nem comentários | `--perfil avaliador --validade 2026-12-15` |

- O nome do curso deve ser igual ao `NOME_CURSO` do TOTVS.
- O `--codprof` é o `CODPROF` do professor no TOTVS.
- Para desativar: `python scripts/criar_usuario.py login --desativar`.
- As senhas ficam só como hash bcrypt em `config/usuarios.yaml`.

## Regras de cálculo

| Resposta | Grupo |
|---|---|
| Concordo totalmente / parcialmente; nota 4–5; "Sim" (com ou sem ressalvas) | Favorável |
| Indiferente / Neutro; nota 3 | Neutro |
| Discordo parcialmente / totalmente; nota 1–2; "Não" | Desfavorável |
| Não se aplica; comentários | fora dos percentuais |

- `% Favorável = respostas favoráveis ÷ respostas válidas`.
- **Questionários** contam `ID_RESPONDENTE` distintos: na avaliação docente, cada professor avaliado
  é um questionário (não é o número de alunos).
- Textos informativos (resposta `ENTENDI`) são removidos.
- A questão de nota global usa o código da resposta (1 a 5); a de indicação usa o texto, porque
  nela o código está invertido (1 = Sim).
- Grupos com menos de `MIN_RESPONDENTES` (padrão 5) não exibem resultado nem comentários.

## Separação das provas

A consulta SQL entrega `TIPO_AVALIACAO` = `CURSO_INFRAESTRUTURA` para as duas provas institucionais.
O sistema separa em `TIPO_PROVA`:

| TIPO_PROVA | Regra | Página |
|---|---|---|
| DOCENTE | `TIPO_AVALIACAO = DOCENTE_DISCIPLINA` | Avaliação Docente |
| INFRAESTRUTURA | nome da prova contém "Infraestrutura" (ou código em `PROVAS_INFRAESTRUTURA`) | Infraestrutura |
| CURSO | demais provas institucionais ("Especificidades do Curso") | Avaliação do Curso |

## Moderação dos comentários

Na página Comentários, a CPA tem a aba **Moderação**:

- **Sem conteúdo**: menos letras que o mínimo configurado (ex.: ".", "-") ou respostas da lista
  ("nada a declarar", "ok"…).
- **Palavras bloqueadas**: comparação sem acento e sem diferenciar maiúsculas; termine com `*` para pegar
  variações. Escolha entre ocultar o comentário ou trocar a palavra por `***`.
- **Ocultar manualmente**: marque comentários específicos (por exemplo, um texto que identifica o aluno).

As regras valem para todas as telas e ficam em `config/moderacao.yaml`.

## Auditoria

Na página **Auditoria dos Dados** (só CPA) e no arquivo `sql/auditoria_totvs.sql`:

1. Caminho dos dados (linhas da API → linhas usadas), para comparar com a execução da consulta no RM.
2. Totais por prova e período, para comparar com a consulta 2.
3. Checagens automáticas: duplicidade, questionário com mais de um curso/prova, docente sem professor,
   semestre divergente, alternativas desconhecidas, aluno respondendo prova de outro curso, questionários
   incompletos.
4. Linha do tempo (dia e hora), quando a consulta SQL passar a trazer `DATA_RESPOSTA` (consulta 10).
5. Investigação por curso, com as consultas 6 e 7 para medir participação.
6. Conferência de um questionário pelo ID (`BH.ID` no RM).

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

## Colocando no servidor

- **Docker**: `docker build -t cpa .` e
  `docker run -d -p 8501:8501 --env-file .env -v ./config:/app/config -v ./data:/app/data cpa`.
- Publique **somente na rede interna** ou atrás de VPN, com um proxy reverso (IIS, Nginx) fazendo HTTPS.
- A pasta `data/` guarda os comentários dos alunos: restrinja o acesso a ela no servidor.
- Use na API um usuário do TOTVS **exclusivo para leitura**, com permissão apenas na consulta da CPA.
- Nunca versione `.env` e `config/usuarios.yaml` (já estão no `.gitignore`).

## Próximos passos sugeridos

- **Taxa de participação**: criar uma consulta no RM com o total de matriculados por curso e
  semestre, e dividir os respondentes por ela.
- **Login com contas da instituição** (Microsoft/Google) via `st.login`, no lugar do arquivo de usuários.
- **Envio automático** de um resumo por e-mail para cada coordenador ao fim do período de avaliação.
