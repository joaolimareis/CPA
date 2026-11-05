/* =====================================================================
   CONSULTAS DE TESTE - AVALIAÇÃO 2026/2 (SOMENTE LEITURA)
   ---------------------------------------------------------------------
   Nenhuma consulta altera dados. Cada bloco é UM SELECT: cadastre cada
   um como uma consulta separada no RM (ex.: TESTE.T1, TESTE.T2...).
   Só a T4 traz dados de aluno (uso interno da CPA, não compartilhar).
   ===================================================================== */


/* ---------------------------------------------------------------------
   T1. FOTO DOS SEMESTRES (rode hoje, guarde o resultado e rode de novo
   daqui a alguns dias). Se os números de 2026/1 e anteriores não mudarem,
   as respostas de hoje NÃO estão alterando os gráficos antigos.
   --------------------------------------------------------------------- */
SELECT PL.NOME                       AS PERIODO_DA_PROVA,
       P.CODPROVA,
       P.NOME                        AS PROVA,
       COUNT(DISTINCT BH.ID)         AS QUESTIONARIOS,
       COUNT(DISTINCT BH.CODPESSOA)  AS ALUNOS
FROM   BHISTORICO BH
       INNER JOIN BPROVA P   ON P.CODCOLIGADA = BH.CODCOLIGADA AND P.CODPROVA = BH.CODPROVA
       INNER JOIN BPERIODO PL ON PL.CODCOLIGADA = BH.CODCOLIGADA AND PL.CODPROVA = BH.CODPROVA
                             AND PL.CODPERIODO = BH.CODPERIODO
WHERE  BH.CODCOLIGADA = 5
  AND  BH.CODAREA = '8'
GROUP  BY PL.NOME, P.CODPROVA, P.NOME
ORDER  BY PL.NOME, P.CODPROVA


/* ---------------------------------------------------------------------
   T2. QUANTO DO DESGASTE É PROFESSOR ANTIGO, POR PROVA
   Para cada prova do 2026/2: quantos alunos têm avaliação pendente, quantos
   professores do semestre atual e de semestres anteriores cada aluno tem
   na lista, em média, e o maior número de professores antigos de um aluno.
   --------------------------------------------------------------------- */
SELECT P.CODPROVA,
       P.NOME                              AS PROVA,
       COUNT(*)                            AS ALUNOS_COM_PENDENCIA,
       CAST(AVG(X.ATUAIS * 1.0)  AS DECIMAL(6,1)) AS MEDIA_PROF_ATUAIS_POR_ALUNO,
       CAST(AVG(X.ANTIGOS * 1.0) AS DECIMAL(6,1)) AS MEDIA_PROF_ANTIGOS_POR_ALUNO,
       MAX(X.ANTIGOS)                      AS MAIOR_QTD_ANTIGOS_DE_UM_ALUNO,
       SUM(CASE WHEN X.ATUAIS = 0 THEN 1 ELSE 0 END) AS ALUNOS_SO_COM_ANTIGOS
FROM  (SELECT BE.CODCOLIGADA, BE.CODPROVA, BE.CODPESSOA,
              SUM(CASE WHEN LEFT(PLTD.CODPERLET, 6) = LEFT(BP.NOME, 6) THEN 1 ELSE 0 END)  AS ATUAIS,
              SUM(CASE WHEN LEFT(PLTD.CODPERLET, 6) <> LEFT(BP.NOME, 6) THEN 1 ELSE 0 END) AS ANTIGOS
       FROM   BEXECPROVA BE
              INNER JOIN BPERIODO BP ON BP.CODCOLIGADA = BE.CODCOLIGADA AND BP.CODPROVA = BE.CODPROVA
                                    AND BP.CODPERIODO = BE.CODPERIODO
              INNER JOIN SOBJETOAVALIADO SOA ON SOA.CODCOLIGADA = BE.CODCOLIGADA
                                            AND SOA.SEQOBJETOAVALIADO = BE.SEQOBJETOAVALIADO
              INNER JOIN STURMADISC TD ON TD.CODCOLIGADA = SOA.CODCOLIGADA AND TD.IDTURMADISC = SOA.IDTURMADISC
              INNER JOIN SPLETIVO PLTD ON PLTD.CODCOLIGADA = TD.CODCOLIGADA AND PLTD.IDPERLET = TD.IDPERLET
       WHERE  BE.CODCOLIGADA = 5
         AND  LEFT(BP.NOME, 6) = '2026/2'
         AND  SOA.CODPROF IS NOT NULL
       GROUP  BY BE.CODCOLIGADA, BE.CODPROVA, BE.CODPESSOA) X
       INNER JOIN BPROVA P ON P.CODCOLIGADA = X.CODCOLIGADA AND P.CODPROVA = X.CODPROVA
GROUP  BY P.CODPROVA, P.NOME
ORDER  BY P.CODPROVA


/* ---------------------------------------------------------------------
   T3. QUANTAS PENDÊNCIAS SAIRIAM SE A LIMPEZA FOSSE FEITA (só conta)
   Mostra, por prova, quantas ligações pendentes são do semestre atual
   (ficam) e quantas são de semestres anteriores (sairiam).
   --------------------------------------------------------------------- */
SELECT P.CODPROVA,
       P.NOME AS PROVA,
       SUM(CASE WHEN LEFT(PLTD.CODPERLET, 6) = LEFT(BP.NOME, 6) THEN 1 ELSE 0 END)  AS FICAM,
       SUM(CASE WHEN LEFT(PLTD.CODPERLET, 6) <> LEFT(BP.NOME, 6) THEN 1 ELSE 0 END) AS SAIRIAM
FROM   BEXECPROVA BE
       INNER JOIN BPERIODO BP ON BP.CODCOLIGADA = BE.CODCOLIGADA AND BP.CODPROVA = BE.CODPROVA
                             AND BP.CODPERIODO = BE.CODPERIODO
       INNER JOIN BPROVA P ON P.CODCOLIGADA = BE.CODCOLIGADA AND P.CODPROVA = BE.CODPROVA
       INNER JOIN SOBJETOAVALIADO SOA ON SOA.CODCOLIGADA = BE.CODCOLIGADA
                                     AND SOA.SEQOBJETOAVALIADO = BE.SEQOBJETOAVALIADO
       INNER JOIN STURMADISC TD ON TD.CODCOLIGADA = SOA.CODCOLIGADA AND TD.IDTURMADISC = SOA.IDTURMADISC
       INNER JOIN SPLETIVO PLTD ON PLTD.CODCOLIGADA = TD.CODCOLIGADA AND PLTD.IDPERLET = TD.IDPERLET
WHERE  BE.CODCOLIGADA = 5
  AND  LEFT(BP.NOME, 6) = '2026/2'
  AND  SOA.CODPROF IS NOT NULL
GROUP  BY P.CODPROVA, P.NOME
ORDER  BY P.CODPROVA


/* ---------------------------------------------------------------------
   T4. O QUE UM ALUNO ESPECÍFICO ESTÁ VENDO (uso interno)
   Troque o RA. Lista os professores pendentes do aluno, com o semestre da
   disciplina. Use com o RA de um aluno que reclamou, para confirmar.
   --------------------------------------------------------------------- */
SELECT P.NOME              AS PROVA,
       PR.NOME             AS PROFESSOR,
       D.NOME              AS DISCIPLINA,
       PLTD.CODPERLET      AS SEMESTRE_DA_DISCIPLINA,
       CASE WHEN LEFT(PLTD.CODPERLET, 6) = LEFT(BP.NOME, 6) THEN 'ATUAL' ELSE 'ANTIGO' END AS SITUACAO
FROM   BEXECPROVA BE
       INNER JOIN SALUNO A ON A.CODCOLIGADA = BE.CODCOLIGADA AND A.CODPESSOA = BE.CODPESSOA
       INNER JOIN BPERIODO BP ON BP.CODCOLIGADA = BE.CODCOLIGADA AND BP.CODPROVA = BE.CODPROVA
                             AND BP.CODPERIODO = BE.CODPERIODO
       INNER JOIN BPROVA P ON P.CODCOLIGADA = BE.CODCOLIGADA AND P.CODPROVA = BE.CODPROVA
       INNER JOIN SOBJETOAVALIADO SOA ON SOA.CODCOLIGADA = BE.CODCOLIGADA
                                     AND SOA.SEQOBJETOAVALIADO = BE.SEQOBJETOAVALIADO
       INNER JOIN STURMADISC TD ON TD.CODCOLIGADA = SOA.CODCOLIGADA AND TD.IDTURMADISC = SOA.IDTURMADISC
       INNER JOIN SPLETIVO PLTD ON PLTD.CODCOLIGADA = TD.CODCOLIGADA AND PLTD.IDPERLET = TD.IDPERLET
       LEFT  JOIN SDISCIPLINA D ON D.CODCOLIGADA = TD.CODCOLIGADA AND D.CODDISC = TD.CODDISC
       LEFT  JOIN SPROFESSOR SP ON SP.CODCOLIGADA = SOA.CODCOLIGADA AND SP.CODPROF = SOA.CODPROF
       LEFT  JOIN PPESSOA PR ON PR.CODIGO = SP.CODPESSOA
WHERE  BE.CODCOLIGADA = 5
  AND  LEFT(BP.NOME, 6) = '2026/2'
  AND  SOA.CODPROF IS NOT NULL
  AND  A.RA = '000000'                 -- <== RA do aluno
ORDER  BY SITUACAO DESC, PLTD.CODPERLET DESC, PR.NOME


/* ---------------------------------------------------------------------
   T5. SITUAÇÃO DOS ALUNOS QUE RECEBERAM A AVALIAÇÃO DO 2026/2
   Para cada aluno com avaliação pendente: o status da matrícula no período
   (SMATRICPL) e o status no curso (SHABILITACAOALUNO). Mostra quantos
   alunos "matriculados" já não estão mais no curso.
   SEM MATRÍCULA NO SEMESTRE = não tem matrícula 2026/2 nos 6 cursos.
   --------------------------------------------------------------------- */
SELECT ISNULL(MAT.CURSO, '(sem matrícula no semestre)')       AS CURSO,
       ISNULL(MAT.STATUS_MATRICULA, '-')                      AS STATUS_MATRICULA,
       ISNULL(MAT.STATUS_CURSO, '-')                          AS STATUS_NO_CURSO,
       COUNT(DISTINCT X.CODPESSOA)                            AS ALUNOS
FROM  (SELECT DISTINCT BE.CODCOLIGADA, BE.CODPESSOA
       FROM   BEXECPROVA BE
              INNER JOIN BPERIODO BP ON BP.CODCOLIGADA = BE.CODCOLIGADA AND BP.CODPROVA = BE.CODPROVA
                                    AND BP.CODPERIODO = BE.CODPERIODO
       WHERE  BE.CODCOLIGADA = 5
         AND  LEFT(BP.NOME, 6) = '2026/2') X
       LEFT JOIN SALUNO A ON A.CODCOLIGADA = X.CODCOLIGADA AND A.CODPESSOA = X.CODPESSOA
       OUTER APPLY (
           SELECT TOP 1 C.NOME AS CURSO, SM.DESCRICAO AS STATUS_MATRICULA, SC.DESCRICAO AS STATUS_CURSO
           FROM   SMATRICPL M
                  INNER JOIN SPLETIVO PLM ON PLM.CODCOLIGADA = M.CODCOLIGADA AND PLM.IDPERLET = M.IDPERLET
                                         AND PLM.CODFILIAL = M.CODFILIAL
                  INNER JOIN SSTATUS SM ON SM.CODCOLIGADA = M.CODCOLIGADA AND SM.CODSTATUS = M.CODSTATUS
                  INNER JOIN SHABILITACAOFILIAL HF ON HF.CODCOLIGADA = M.CODCOLIGADA
                                                  AND HF.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
                  INNER JOIN SCURSO C ON C.CODCOLIGADA = HF.CODCOLIGADA AND C.CODCURSO = HF.CODCURSO
                  LEFT  JOIN SHABILITACAOALUNO HA ON HA.CODCOLIGADA = M.CODCOLIGADA AND HA.RA = M.RA
                                                 AND HA.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
                  LEFT  JOIN SSTATUS SC ON SC.CODCOLIGADA = HA.CODCOLIGADA AND SC.CODSTATUS = HA.CODSTATUS
           WHERE  M.CODCOLIGADA = A.CODCOLIGADA
             AND  M.RA = A.RA
             AND  LEFT(PLM.CODPERLET, 6) = '2026/2'
             AND  C.NOME IN ('Análise e Desenvolvimento de Sistemas', 'Direito', 'Enfermagem', 'Pedagogia',
                             'Psicologia', 'Teologia')
           ORDER  BY CASE WHEN UPPER(LTRIM(RTRIM(SC.DESCRICAO))) = 'CURSANDO' THEN 0 ELSE 1 END
       ) MAT
GROUP  BY ISNULL(MAT.CURSO, '(sem matrícula no semestre)'), ISNULL(MAT.STATUS_MATRICULA, '-'),
          ISNULL(MAT.STATUS_CURSO, '-')
ORDER  BY CURSO, ALUNOS DESC


/* ---------------------------------------------------------------------
   T6. SITUAÇÃO DOS ALUNOS QUE JÁ RESPONDERAM NO 2026/2
   Igual à T5, mas para quem já respondeu. Mostra se respostas de alunos
   que saíram do curso estão entrando nos resultados.
   --------------------------------------------------------------------- */
SELECT ISNULL(MAT.CURSO, '(sem matrícula no semestre)')       AS CURSO,
       ISNULL(MAT.STATUS_MATRICULA, '-')                      AS STATUS_MATRICULA,
       ISNULL(MAT.STATUS_CURSO, '-')                          AS STATUS_NO_CURSO,
       COUNT(DISTINCT X.CODPESSOA)                            AS ALUNOS,
       SUM(X.QUESTIONARIOS)                                   AS QUESTIONARIOS
FROM  (SELECT BH.CODCOLIGADA, BH.CODPESSOA, COUNT(DISTINCT BH.ID) AS QUESTIONARIOS
       FROM   BHISTORICO BH
              INNER JOIN BPERIODO PL ON PL.CODCOLIGADA = BH.CODCOLIGADA AND PL.CODPROVA = BH.CODPROVA
                                    AND PL.CODPERIODO = BH.CODPERIODO
       WHERE  BH.CODCOLIGADA = 5
         AND  BH.CODAREA = '8'
         AND  LEFT(PL.NOME, 6) = '2026/2'
       GROUP  BY BH.CODCOLIGADA, BH.CODPESSOA) X
       LEFT JOIN SALUNO A ON A.CODCOLIGADA = X.CODCOLIGADA AND A.CODPESSOA = X.CODPESSOA
       OUTER APPLY (
           SELECT TOP 1 C.NOME AS CURSO, SM.DESCRICAO AS STATUS_MATRICULA, SC.DESCRICAO AS STATUS_CURSO
           FROM   SMATRICPL M
                  INNER JOIN SPLETIVO PLM ON PLM.CODCOLIGADA = M.CODCOLIGADA AND PLM.IDPERLET = M.IDPERLET
                                         AND PLM.CODFILIAL = M.CODFILIAL
                  INNER JOIN SSTATUS SM ON SM.CODCOLIGADA = M.CODCOLIGADA AND SM.CODSTATUS = M.CODSTATUS
                  INNER JOIN SHABILITACAOFILIAL HF ON HF.CODCOLIGADA = M.CODCOLIGADA
                                                  AND HF.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
                  INNER JOIN SCURSO C ON C.CODCOLIGADA = HF.CODCOLIGADA AND C.CODCURSO = HF.CODCURSO
                  LEFT  JOIN SHABILITACAOALUNO HA ON HA.CODCOLIGADA = M.CODCOLIGADA AND HA.RA = M.RA
                                                 AND HA.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
                  LEFT  JOIN SSTATUS SC ON SC.CODCOLIGADA = HA.CODCOLIGADA AND SC.CODSTATUS = HA.CODSTATUS
           WHERE  M.CODCOLIGADA = A.CODCOLIGADA
             AND  M.RA = A.RA
             AND  LEFT(PLM.CODPERLET, 6) = '2026/2'
             AND  C.NOME IN ('Análise e Desenvolvimento de Sistemas', 'Direito', 'Enfermagem', 'Pedagogia',
                             'Psicologia', 'Teologia')
           ORDER  BY CASE WHEN UPPER(LTRIM(RTRIM(SC.DESCRICAO))) = 'CURSANDO' THEN 0 ELSE 1 END
       ) MAT
GROUP  BY ISNULL(MAT.CURSO, '(sem matrícula no semestre)'), ISNULL(MAT.STATUS_MATRICULA, '-'),
          ISNULL(MAT.STATUS_CURSO, '-')
ORDER  BY CURSO, ALUNOS DESC


/* ---------------------------------------------------------------------
   T7. MATRICULADOS DO 2026/2 POR STATUS (base do ranking de participação)
   Todos os alunos com matrícula no 2026/2 nos 6 cursos, por status da
   matrícula e status no curso. Serve para decidir quais combinações devem
   contar como "matriculado" no ranking.
   --------------------------------------------------------------------- */
SELECT C.NOME                        AS CURSO,
       SM.DESCRICAO                  AS STATUS_MATRICULA,
       ISNULL(SC.DESCRICAO, '-')     AS STATUS_NO_CURSO,
       COUNT(DISTINCT M.RA)          AS ALUNOS
FROM   SMATRICPL M
       INNER JOIN SPLETIVO PLM ON PLM.CODCOLIGADA = M.CODCOLIGADA AND PLM.IDPERLET = M.IDPERLET
                              AND PLM.CODFILIAL = M.CODFILIAL
       INNER JOIN SSTATUS SM ON SM.CODCOLIGADA = M.CODCOLIGADA AND SM.CODSTATUS = M.CODSTATUS
       INNER JOIN SHABILITACAOFILIAL HF ON HF.CODCOLIGADA = M.CODCOLIGADA
                                       AND HF.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
       INNER JOIN SCURSO C ON C.CODCOLIGADA = HF.CODCOLIGADA AND C.CODCURSO = HF.CODCURSO
       LEFT  JOIN SHABILITACAOALUNO HA ON HA.CODCOLIGADA = M.CODCOLIGADA AND HA.RA = M.RA
                                      AND HA.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
       LEFT  JOIN SSTATUS SC ON SC.CODCOLIGADA = HA.CODCOLIGADA AND SC.CODSTATUS = HA.CODSTATUS
WHERE  M.CODCOLIGADA = 5
  AND  LEFT(PLM.CODPERLET, 6) = '2026/2'
  AND  C.NOME IN ('Análise e Desenvolvimento de Sistemas', 'Direito', 'Enfermagem', 'Pedagogia',
                  'Psicologia', 'Teologia')
GROUP  BY C.NOME, SM.DESCRICAO, ISNULL(SC.DESCRICAO, '-')
ORDER  BY C.NOME, ALUNOS DESC
