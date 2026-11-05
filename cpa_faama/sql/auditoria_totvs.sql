/* =====================================================================
   AUDITORIA DA AVALIAÇÃO INSTITUCIONAL (CPA) - CONSULTAS PARA O TOTVS RM
   ---------------------------------------------------------------------
   Rode cada bloco separadamente (no RM: Consultas SQL, ou no SQL Server
   Management Studio) e compare com a página "Auditoria dos Dados" do sistema.

   ATENÇÃO: estas consultas trazem dados identificáveis (CODPESSOA, RA).
   Use só para conferência interna da CPA; não exporte nem compartilhe.

   Ajuste os filtros de coligada (5), área (8) e períodos se necessário.
   ===================================================================== */


/* ---------------------------------------------------------------------
   1. DESCOBRIR OS CAMPOS DE DATA/HORA DAS TABELAS DE AVALIAÇÃO
   Mostra quais colunas de data existem. Na maioria das tabelas do RM há
   RECCREATEDON (data de criação do registro) e RECMODIFIEDON (última
   alteração). Confirme aqui antes de usar as consultas 5 e 10.
   --------------------------------------------------------------------- */
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM   INFORMATION_SCHEMA.COLUMNS
WHERE  TABLE_NAME IN ('BHISTORICO', 'BHISTRESPPROVA', 'BPERIODO', 'BPROVA')
  AND  DATA_TYPE IN ('date', 'datetime', 'datetime2', 'smalldatetime')
ORDER  BY TABLE_NAME, COLUMN_NAME;


/* ---------------------------------------------------------------------
   2. TOTAIS POR PROVA E PERÍODO, DIRETO NAS TABELAS (SEM OS FILTROS DA CPA)
   Compare QUESTIONARIOS com a seção 2 da Auditoria.
   - Aqui entram todos os respondentes; a consulta da CPA filtra matrícula,
     status, pensionato e turmas de etapa. Por isso o sistema pode ter menos.
   - ALUNOS_DISTINTOS mostra quantas pessoas responderam (na avaliação
     docente, um aluno gera vários questionários: um por professor).
   --------------------------------------------------------------------- */
SELECT P.CODPROVA,
       P.NOME                        AS NOME_PROVA,
       PL.NOME                       AS PERIODO_PROVA,
       COUNT(DISTINCT BH.ID)         AS QUESTIONARIOS,
       COUNT(DISTINCT BH.CODPESSOA)  AS ALUNOS_DISTINTOS,
       COUNT(*)                      AS LINHAS_RESPOSTA
FROM   BHISTRESPPROVA BHRP
       INNER JOIN BHISTORICO BH
               ON BH.CODCOLIGADA = BHRP.CODCOLIGADA
              AND BH.CODAREA = BHRP.CODAREA
              AND BH.CODMATERIA = BHRP.CODMATERIA
              AND BH.CODQUESTAO = BHRP.CODQUESTAO
              AND BH.ID = BHRP.ID
       INNER JOIN BPROVA P
               ON P.CODCOLIGADA = BH.CODCOLIGADA
              AND P.CODPROVA = BH.CODPROVA
       INNER JOIN BPERIODO PL
               ON PL.CODCOLIGADA = BH.CODCOLIGADA
              AND PL.CODPROVA = BH.CODPROVA
              AND PL.CODPERIODO = BH.CODPERIODO
WHERE  BHRP.CODCOLIGADA = 5
  AND  BHRP.CODAREA = '8'
  AND  PL.NOME IN ('2026/1', '2026/1T', '2026/2', '2026/2T')
GROUP  BY P.CODPROVA, P.NOME, PL.NOME
ORDER  BY P.CODPROVA, PL.NOME;


/* ---------------------------------------------------------------------
   3. TOTAL DE LINHAS DA CONSULTA DA CPA
   Não precisa de SQL: execute a consulta FAAMACPA.6 dentro do RM e compare
   o total de registros com "Linhas recebidas da API" (seção 1 da Auditoria).
   Se os números forem iguais, a API está entregando tudo o que a consulta gera.
   --------------------------------------------------------------------- */


/* ---------------------------------------------------------------------
   4. RESPOSTAS DUPLICADAS NAS TABELAS DO RM
   Deve retornar vazio. Se trouxer linhas, o próprio RM tem a mesma questão
   gravada duas vezes no mesmo questionário.
   --------------------------------------------------------------------- */
SELECT BHRP.ID, BHRP.CODMATERIA, BHRP.CODQUESTAO, COUNT(*) AS VEZES
FROM   BHISTRESPPROVA BHRP
WHERE  BHRP.CODCOLIGADA = 5
  AND  BHRP.CODAREA = '8'
GROUP  BY BHRP.ID, BHRP.CODMATERIA, BHRP.CODQUESTAO
HAVING COUNT(*) > 1;


/* ---------------------------------------------------------------------
   5. QUANDO AS RESPOSTAS FORAM DADAS (DIA E HORA)
   Usa RECCREATEDON da BHISTORICO. Se a consulta 1 mostrar outro campo de
   data mais adequado, troque nas três ocorrências abaixo.
   --------------------------------------------------------------------- */
-- 5a. Questionários iniciados por dia e hora
SELECT CONVERT(date, MIN(BH.RECCREATEDON))   AS DIA,
       DATEPART(HOUR, MIN(BH.RECCREATEDON))  AS HORA,
       P.NOME                                AS NOME_PROVA,
       BH.ID
INTO   #INICIO_QUESTIONARIO
FROM   BHISTORICO BH
       INNER JOIN BPROVA P ON P.CODCOLIGADA = BH.CODCOLIGADA AND P.CODPROVA = BH.CODPROVA
       INNER JOIN BPERIODO PL ON PL.CODCOLIGADA = BH.CODCOLIGADA AND PL.CODPROVA = BH.CODPROVA
                             AND PL.CODPERIODO = BH.CODPERIODO
WHERE  BH.CODCOLIGADA = 5
  AND  BH.CODAREA = '8'
  AND  PL.NOME IN ('2026/1', '2026/1T', '2026/2', '2026/2T')
GROUP  BY P.NOME, BH.ID;

SELECT DIA, HORA, NOME_PROVA, COUNT(*) AS QUESTIONARIOS
FROM   #INICIO_QUESTIONARIO
GROUP  BY DIA, HORA, NOME_PROVA
ORDER  BY DIA, HORA, NOME_PROVA;

-- 5b. Primeira e última resposta de cada prova
SELECT NOME_PROVA, MIN(DIA) AS PRIMEIRO_DIA, MAX(DIA) AS ULTIMO_DIA, COUNT(*) AS QUESTIONARIOS
FROM   #INICIO_QUESTIONARIO
GROUP  BY NOME_PROVA
ORDER  BY PRIMEIRO_DIA;

DROP TABLE #INICIO_QUESTIONARIO;


/* ---------------------------------------------------------------------
   6. TEOLOGIA: PARTICIPAÇÃO (MATRICULADOS x RESPONDENTES)
   Mostra se o número baixo de respostas é falta de participação ou perda
   de dados. Troque 'Teologia' para investigar outro curso.
   --------------------------------------------------------------------- */
-- 6a. Alunos matriculados no curso por período e status
SELECT PLM.CODPERLET, ST.DESCRICAO AS STATUS, COUNT(DISTINCT M.RA) AS ALUNOS
FROM   SMATRICPL M
       INNER JOIN SPLETIVO PLM ON PLM.CODCOLIGADA = M.CODCOLIGADA AND PLM.IDPERLET = M.IDPERLET
                              AND PLM.CODFILIAL = M.CODFILIAL
       INNER JOIN SSTATUS ST ON ST.CODCOLIGADA = M.CODCOLIGADA AND ST.CODSTATUS = M.CODSTATUS
       INNER JOIN SHABILITACAOFILIAL HF ON HF.CODCOLIGADA = M.CODCOLIGADA
                                       AND HF.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
       INNER JOIN SCURSO C ON C.CODCOLIGADA = HF.CODCOLIGADA AND C.CODCURSO = HF.CODCURSO
WHERE  M.CODCOLIGADA = 5
  AND  C.NOME = 'Teologia'
  AND  PLM.CODPERLET IN ('2026/1', '2026/1T')
GROUP  BY PLM.CODPERLET, ST.DESCRICAO
ORDER  BY PLM.CODPERLET, ST.DESCRICAO;

-- 6b. Quantos desses alunos responderam cada prova
SELECT P.CODPROVA, P.NOME AS NOME_PROVA, PL.NOME AS PERIODO_PROVA,
       COUNT(DISTINCT BH.CODPESSOA) AS ALUNOS_QUE_RESPONDERAM,
       COUNT(DISTINCT BH.ID)        AS QUESTIONARIOS
FROM   BHISTORICO BH
       INNER JOIN BPROVA P ON P.CODCOLIGADA = BH.CODCOLIGADA AND P.CODPROVA = BH.CODPROVA
       INNER JOIN BPERIODO PL ON PL.CODCOLIGADA = BH.CODCOLIGADA AND PL.CODPROVA = BH.CODPROVA
                             AND PL.CODPERIODO = BH.CODPERIODO
       INNER JOIN SALUNO A ON A.CODCOLIGADA = BH.CODCOLIGADA AND A.CODPESSOA = BH.CODPESSOA
WHERE  BH.CODCOLIGADA = 5
  AND  BH.CODAREA = '8'
  AND  PL.NOME IN ('2026/1', '2026/1T')
  AND  EXISTS (
        SELECT 1
        FROM   SMATRICPL M
               INNER JOIN SPLETIVO PLM ON PLM.CODCOLIGADA = M.CODCOLIGADA AND PLM.IDPERLET = M.IDPERLET
                                      AND PLM.CODFILIAL = M.CODFILIAL
               INNER JOIN SHABILITACAOFILIAL HF ON HF.CODCOLIGADA = M.CODCOLIGADA
                                               AND HF.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
               INNER JOIN SCURSO C ON C.CODCOLIGADA = HF.CODCOLIGADA AND C.CODCURSO = HF.CODCURSO
        WHERE  M.CODCOLIGADA = A.CODCOLIGADA
          AND  M.RA = A.RA
          AND  C.NOME = 'Teologia'
          AND  PLM.CODPERLET IN ('2026/1', '2026/1T'))
GROUP  BY P.CODPROVA, P.NOME, PL.NOME
ORDER  BY P.CODPROVA;


/* ---------------------------------------------------------------------
   7. TEOLOGIA: TAXA DE RESPOSTA POR PROFESSOR, DISCIPLINA E TURMA
   Para cada professor/disciplina que tinha avaliação aberta, compara os
   alunos da turma com as avaliações respondidas. Ajuste o filtro da turma
   (no seu RM, as turmas de Teologia começam com GBTEO).
   --------------------------------------------------------------------- */
SELECT TD.CODTURMA,
       D.NOME                               AS DISCIPLINA,
       PP.NOME                              AS PROFESSOR,
       PLT.CODPERLET,
       (SELECT COUNT(DISTINCT MAT.RA)
        FROM   SMATRICULA MAT
        WHERE  MAT.CODCOLIGADA = TD.CODCOLIGADA
          AND  MAT.IDTURMADISC = TD.IDTURMADISC) AS ALUNOS_NA_DISCIPLINA,
       COUNT(DISTINCT BH.ID)                AS AVALIACOES_RESPONDIDAS
FROM   SOBJETOAVALIADO SOA
       INNER JOIN STURMADISC TD ON TD.CODCOLIGADA = SOA.CODCOLIGADA AND TD.IDTURMADISC = SOA.IDTURMADISC
       INNER JOIN SPLETIVO PLT ON PLT.CODCOLIGADA = TD.CODCOLIGADA AND PLT.IDPERLET = TD.IDPERLET
       LEFT  JOIN SDISCIPLINA D ON D.CODCOLIGADA = TD.CODCOLIGADA AND D.CODDISC = TD.CODDISC
       LEFT  JOIN SPROFESSOR PR ON PR.CODCOLIGADA = SOA.CODCOLIGADA AND PR.CODPROF = SOA.CODPROF
       LEFT  JOIN PPESSOA PP ON PP.CODIGO = PR.CODPESSOA
       LEFT  JOIN BHISTORICO BH ON BH.CODCOLIGADA = SOA.CODCOLIGADA
                               AND BH.SEQOBJETOAVALIADO = SOA.SEQOBJETOAVALIADO
                               AND BH.CODAREA = '8'
WHERE  SOA.CODCOLIGADA = 5
  AND  SOA.CODPROF IS NOT NULL
  AND  PLT.CODPERLET IN ('2026/1', '2026/1T')
  AND  TD.CODTURMA LIKE 'GBTEO%'
GROUP  BY TD.CODCOLIGADA, TD.IDTURMADISC, TD.CODTURMA, D.NOME, PP.NOME, PLT.CODPERLET
ORDER  BY TD.CODTURMA, D.NOME;


/* ---------------------------------------------------------------------
   8. RESPOSTAS QUE FICAM FORA DA CONSULTA DA CPA
   8a: respondentes sem cadastro de aluno (SALUNO).
   8b: alunos sem matrícula no mesmo semestre da prova.
   Os dois casos não aparecem no sistema. Se os números forem altos,
   vale revisar a regra de matrícula da consulta.
   --------------------------------------------------------------------- */
-- 8a
SELECT P.NOME AS NOME_PROVA, PL.NOME AS PERIODO_PROVA, COUNT(DISTINCT BH.ID) AS QUESTIONARIOS
FROM   BHISTORICO BH
       INNER JOIN BPROVA P ON P.CODCOLIGADA = BH.CODCOLIGADA AND P.CODPROVA = BH.CODPROVA
       INNER JOIN BPERIODO PL ON PL.CODCOLIGADA = BH.CODCOLIGADA AND PL.CODPROVA = BH.CODPROVA
                             AND PL.CODPERIODO = BH.CODPERIODO
WHERE  BH.CODCOLIGADA = 5
  AND  BH.CODAREA = '8'
  AND  PL.NOME IN ('2026/1', '2026/1T', '2026/2', '2026/2T')
  AND  NOT EXISTS (SELECT 1 FROM SALUNO A
                   WHERE A.CODCOLIGADA = BH.CODCOLIGADA AND A.CODPESSOA = BH.CODPESSOA)
GROUP  BY P.NOME, PL.NOME;

-- 8b
SELECT P.NOME AS NOME_PROVA, PL.NOME AS PERIODO_PROVA, COUNT(DISTINCT BH.ID) AS QUESTIONARIOS
FROM   BHISTORICO BH
       INNER JOIN BPROVA P ON P.CODCOLIGADA = BH.CODCOLIGADA AND P.CODPROVA = BH.CODPROVA
       INNER JOIN BPERIODO PL ON PL.CODCOLIGADA = BH.CODCOLIGADA AND PL.CODPROVA = BH.CODPROVA
                             AND PL.CODPERIODO = BH.CODPERIODO
       INNER JOIN SALUNO A ON A.CODCOLIGADA = BH.CODCOLIGADA AND A.CODPESSOA = BH.CODPESSOA
WHERE  BH.CODCOLIGADA = 5
  AND  BH.CODAREA = '8'
  AND  PL.NOME IN ('2026/1', '2026/1T', '2026/2', '2026/2T')
  AND  NOT EXISTS (
        SELECT 1
        FROM   SMATRICPL M
               INNER JOIN SPLETIVO PLM ON PLM.CODCOLIGADA = M.CODCOLIGADA AND PLM.IDPERLET = M.IDPERLET
                                      AND PLM.CODFILIAL = M.CODFILIAL
        WHERE  M.CODCOLIGADA = A.CODCOLIGADA
          AND  M.RA = A.RA
          AND  LEFT(PLM.CODPERLET, 6) = LEFT(PL.NOME, 6))
GROUP  BY P.NOME, PL.NOME;


/* ---------------------------------------------------------------------
   9. CONFERIR A SEPARAÇÃO ENTRE AVALIAÇÃO DOCENTE E INSTITUCIONAL
   Provas docentes devem ter COM_PROFESSOR = QUESTIONARIOS.
   Provas de curso e infraestrutura devem ter COM_PROFESSOR = 0.
   --------------------------------------------------------------------- */
SELECT P.CODPROVA, P.NOME AS NOME_PROVA,
       COUNT(DISTINCT BH.ID) AS QUESTIONARIOS,
       COUNT(DISTINCT CASE WHEN SOA.CODPROF IS NOT NULL AND SOA.IDTURMADISC IS NOT NULL
                           THEN BH.ID END) AS COM_PROFESSOR
FROM   BHISTORICO BH
       INNER JOIN BPROVA P ON P.CODCOLIGADA = BH.CODCOLIGADA AND P.CODPROVA = BH.CODPROVA
       INNER JOIN BPERIODO PL ON PL.CODCOLIGADA = BH.CODCOLIGADA AND PL.CODPROVA = BH.CODPROVA
                             AND PL.CODPERIODO = BH.CODPERIODO
       LEFT  JOIN SOBJETOAVALIADO SOA ON SOA.CODCOLIGADA = BH.CODCOLIGADA
                                     AND SOA.SEQOBJETOAVALIADO = BH.SEQOBJETOAVALIADO
WHERE  BH.CODCOLIGADA = 5
  AND  BH.CODAREA = '8'
  AND  PL.NOME IN ('2026/1', '2026/1T', '2026/2', '2026/2T')
GROUP  BY P.CODPROVA, P.NOME
ORDER  BY P.CODPROVA;


/* ---------------------------------------------------------------------
   10. INCLUIR A DATA DA RESPOSTA NA CONSULTA DA CPA (FAAMACPA.6)
   Depois de confirmar o campo na consulta 1, acrescente esta linha nos
   DOIS blocos do UNION ALL (curso/infraestrutura e docente), por exemplo
   logo depois de "BH.ID AS ID_RESPONDENTE,":

       BH.RECCREATEDON AS DATA_RESPOSTA,

   - Precisa estar nos dois blocos, na mesma posição, senão o UNION falha.
   - O sistema reconhece a coluna sozinho e ativa a seção 4 da Auditoria.
   - O Power BI não é afetado: ele só lê as colunas que já conhece.
   --------------------------------------------------------------------- */
