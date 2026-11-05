/* =====================================================================
   CONFERÊNCIA DA CONSULTA DE PARTICIPAÇÃO (FAAMACPA.7)
   ---------------------------------------------------------------------
   Estas consultas mostram ALUNO POR ALUNO (com RA e nome) para você
   conferir os totais. Uso interno da CPA: não exporte nem compartilhe.
   ===================================================================== */


/* ---------------------------------------------------------------------
   1. LISTA DE ALUNOS DE UMA TURMA E QUANTOS QUESTIONÁRIOS CADA UM RESPONDEU
   Troque a turma e o período nas duas linhas marcadas.
   Como conferir:
   - Conte as linhas cujo STATUS não é cancelado/trancado/desistente:
     deve bater com ALUNOS_MATRICULADOS da FAAMACPA.7.
   - Dessas, conte as que têm QUESTIONARIOS > 0: deve bater com ALUNOS_RESPONDERAM.
   - Compare a lista com a relação de alunos da turma no TOTVS Educacional.
   --------------------------------------------------------------------- */
SELECT M.RA,
       PP.NOME                                  AS ALUNO,
       ST.DESCRICAO                             AS STATUS,
       (SELECT COUNT(DISTINCT BH.ID)
        FROM   BHISTORICO BH
               INNER JOIN BPERIODO PL ON PL.CODCOLIGADA = BH.CODCOLIGADA AND PL.CODPROVA = BH.CODPROVA
                                     AND PL.CODPERIODO = BH.CODPERIODO
        WHERE  BH.CODCOLIGADA = M.CODCOLIGADA
          AND  BH.CODPESSOA = A.CODPESSOA
          AND  BH.CODAREA = '8'
          AND  LEFT(PL.NOME, 6) = LEFT(PLM.CODPERLET, 6)) AS QUESTIONARIOS
FROM   SMATRICPL M
       INNER JOIN SPLETIVO PLM ON PLM.CODCOLIGADA = M.CODCOLIGADA AND PLM.IDPERLET = M.IDPERLET
                              AND PLM.CODFILIAL = M.CODFILIAL
       INNER JOIN SSTATUS ST ON ST.CODCOLIGADA = M.CODCOLIGADA AND ST.CODSTATUS = M.CODSTATUS
       INNER JOIN SALUNO A ON A.CODCOLIGADA = M.CODCOLIGADA AND A.RA = M.RA
       INNER JOIN PPESSOA PP ON PP.CODIGO = A.CODPESSOA
WHERE  M.CODCOLIGADA = 5
  AND  M.CODTURMA = 'GTADSI3AN'        -- <== turma
  AND  PLM.CODPERLET = '2026/1'        -- <== período
ORDER  BY PP.NOME;


/* ---------------------------------------------------------------------
   2. ALUNOS QUE AVALIARAM O MESMO PROFESSOR/DISCIPLINA MAIS DE UMA VEZ
   Explica turmas com mais avaliações respondidas do que esperadas
   (ex.: Teologia 1º Período, 728 de 706). Se vier vazio, a causa é outra.
   --------------------------------------------------------------------- */
SELECT A.RA,
       PP.NOME                     AS ALUNO,
       D.NOME                      AS DISCIPLINA,
       PR.NOME                     AS PROFESSOR,
       COUNT(DISTINCT BH.ID)       AS VEZES_QUE_AVALIOU
FROM   BHISTORICO BH
       INNER JOIN BPERIODO PL ON PL.CODCOLIGADA = BH.CODCOLIGADA AND PL.CODPROVA = BH.CODPROVA
                             AND PL.CODPERIODO = BH.CODPERIODO
       INNER JOIN SALUNO A ON A.CODCOLIGADA = BH.CODCOLIGADA AND A.CODPESSOA = BH.CODPESSOA
       INNER JOIN PPESSOA PP ON PP.CODIGO = A.CODPESSOA
       INNER JOIN SOBJETOAVALIADO SOA ON SOA.CODCOLIGADA = BH.CODCOLIGADA
                                     AND SOA.SEQOBJETOAVALIADO = BH.SEQOBJETOAVALIADO
                                     AND SOA.CODPROF IS NOT NULL AND SOA.IDTURMADISC IS NOT NULL
       INNER JOIN STURMADISC TD ON TD.CODCOLIGADA = SOA.CODCOLIGADA AND TD.IDTURMADISC = SOA.IDTURMADISC
       LEFT  JOIN SDISCIPLINA D ON D.CODCOLIGADA = TD.CODCOLIGADA AND D.CODDISC = TD.CODDISC
       LEFT  JOIN SPROFESSOR SP ON SP.CODCOLIGADA = SOA.CODCOLIGADA AND SP.CODPROF = SOA.CODPROF
       LEFT  JOIN PPESSOA PR ON PR.CODIGO = SP.CODPESSOA
WHERE  BH.CODCOLIGADA = 5
  AND  BH.CODAREA = '8'
  AND  LEFT(PL.NOME, 6) = '2026/1'
  AND  A.RA IN (SELECT M.RA
                FROM   SMATRICPL M
                       INNER JOIN SPLETIVO PLM ON PLM.CODCOLIGADA = M.CODCOLIGADA AND PLM.IDPERLET = M.IDPERLET
                                              AND PLM.CODFILIAL = M.CODFILIAL
                WHERE  M.CODCOLIGADA = 5
                  AND  M.CODTURMA = 'GBTEO2T1A'     -- <== turma
                  AND  PLM.CODPERLET = '2026/1T')   -- <== período
GROUP  BY A.RA, PP.NOME, D.NOME, PR.NOME, SOA.SEQOBJETOAVALIADO
HAVING COUNT(DISTINCT BH.ID) > 1
ORDER  BY PP.NOME;


/* ---------------------------------------------------------------------
   3. DISCIPLINAS DE UMA TURMA E SE TINHAM AVALIAÇÃO ABERTA
   Explica turmas com 0 avaliações esperadas (ex.: Enfermagem 1º Período
   Matutino). OBJETOS_AVALIADOS = 0 significa que a disciplina não tinha
   avaliação docente disponível no RM.
   --------------------------------------------------------------------- */
SELECT TD.CODTURMA,
       D.NOME                                   AS DISCIPLINA,
       (SELECT COUNT(DISTINCT MAT.RA) FROM SMATRICULA MAT
        WHERE MAT.CODCOLIGADA = TD.CODCOLIGADA AND MAT.IDTURMADISC = TD.IDTURMADISC) AS ALUNOS,
       (SELECT COUNT(*) FROM SOBJETOAVALIADO SOA
        WHERE SOA.CODCOLIGADA = TD.CODCOLIGADA AND SOA.IDTURMADISC = TD.IDTURMADISC
          AND SOA.CODPROF IS NOT NULL)          AS OBJETOS_AVALIADOS
FROM   STURMADISC TD
       INNER JOIN SPLETIVO PLT ON PLT.CODCOLIGADA = TD.CODCOLIGADA AND PLT.IDPERLET = TD.IDPERLET
       LEFT  JOIN SDISCIPLINA D ON D.CODCOLIGADA = TD.CODCOLIGADA AND D.CODDISC = TD.CODDISC
WHERE  TD.CODCOLIGADA = 5
  AND  TD.CODTURMA = 'GBENF1M1A'       -- <== turma
  AND  PLT.CODPERLET = '2026/1'        -- <== período
ORDER  BY D.NOME;


/* ---------------------------------------------------------------------
   4. TODOS OS STATUS DE MATRÍCULA DO SEMESTRE
   Mostra cada status e quantos alunos estão nele. Marque quais significam
   que o aluno SAIU do curso (esses não devem contar como matriculados).
   Hoje a FAAMACPA.7 desconsidera: Cancelado, Trancado, Desistente,
   Abandono e Desvinculado do curso.
   --------------------------------------------------------------------- */
SELECT ST.DESCRICAO AS STATUS, PLM.CODPERLET, COUNT(DISTINCT M.RA) AS ALUNOS
FROM   SMATRICPL M
       INNER JOIN SPLETIVO PLM ON PLM.CODCOLIGADA = M.CODCOLIGADA AND PLM.IDPERLET = M.IDPERLET
                              AND PLM.CODFILIAL = M.CODFILIAL
       INNER JOIN SSTATUS ST ON ST.CODCOLIGADA = M.CODCOLIGADA AND ST.CODSTATUS = M.CODSTATUS
       INNER JOIN SHABILITACAOFILIAL HF ON HF.CODCOLIGADA = M.CODCOLIGADA
                                       AND HF.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
       INNER JOIN SCURSO C ON C.CODCOLIGADA = HF.CODCOLIGADA AND C.CODCURSO = HF.CODCURSO
WHERE  M.CODCOLIGADA = 5
  AND  PLM.CODPERLET IN ('2026/1', '2026/1T', '2026/2', '2026/2T')
  AND  C.NOME IN ('Análise e Desenvolvimento de Sistemas', 'Direito', 'Enfermagem', 'Pedagogia', 'Psicologia', 'Teologia')
GROUP  BY ST.DESCRICAO, PLM.CODPERLET
ORDER  BY PLM.CODPERLET, ALUNOS DESC;


/* ---------------------------------------------------------------------
   5. AS DUAS AVALIAÇÕES REPETIDAS: EM QUE PERÍODO E QUANDO FORAM FEITAS
   Para os alunos que avaliaram o mesmo professor duas vezes (consulta 2),
   mostra o período de cada aplicação. Ajuda a entender se a avaliação foi
   aberta duas vezes para a turma. Usa RECCREATEDON (confira o nome do
   campo com a consulta 1 do arquivo auditoria_totvs.sql).
   --------------------------------------------------------------------- */
SELECT PL.NOME AS PERIODO_DA_PROVA,
       CONVERT(date, MIN(BH.RECCREATEDON)) AS PRIMEIRO_DIA,
       CONVERT(date, MAX(BH.RECCREATEDON)) AS ULTIMO_DIA,
       COUNT(DISTINCT BH.ID) AS AVALIACOES
FROM   BHISTORICO BH
       INNER JOIN BPERIODO PL ON PL.CODCOLIGADA = BH.CODCOLIGADA AND PL.CODPROVA = BH.CODPROVA
                             AND PL.CODPERIODO = BH.CODPERIODO
WHERE  BH.CODCOLIGADA = 5
  AND  BH.CODAREA = '8'
  AND  BH.CODPROVA = '23'           -- Teologia - Avaliação Docente e Disciplina
GROUP  BY PL.NOME
ORDER  BY PRIMEIRO_DIA;
