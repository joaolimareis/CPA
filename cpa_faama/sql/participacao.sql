/* =====================================================================
   CONSULTA DE PARTICIPAÇÃO (cadastre no RM, ex.: FAAMACPA.7, e informe
   o código em TOTVS_CONSULTA_PARTICIPACAO no .env)
   ---------------------------------------------------------------------
   Uma linha por turma, só com totais. O RA é usado aqui dentro, mas nenhum
   dado individual sai do RM.

   Versão 8: só alunos Cursando (ou Concluído, em semestre encerrado) contam como matriculados.
   Versão 7: pré-matrícula (Portal Liberado, Contrato Assinado, Reserva de Vaga) não conta como matriculado.
   Versão 6: aluno que só avaliou professores de semestres anteriores não conta como participante.
   Versão 5: avaliação docente repetida pelo mesmo aluno conta uma vez só.
   Versão 4: também desconsidera alunos com status Abandono e Desvinculado do curso.
   Versão 3: corrige o erro "Cannot perform an aggregate function..." do SQL Server.
   Versão 2: as avaliações docentes respondidas agora contam só as
   disciplinas da própria matrícula (mesmo critério das esperadas).
   Na versão 1, alunos com duas matrículas no semestre (ex.: Teologia +
   curso de extensão) tinham respondidas maiores que esperadas.
   ===================================================================== */
SELECT
    PLM.CODPERLET,
    LEFT(PLM.CODPERLET, 6)                                          AS SEMESTRE,
    C.NOME                                                          AS NOME_CURSO,
    M.CODTURMA,
    T.NOME                                                          AS NOME_TURMA,
    COUNT(DISTINCT M.RA)                                            AS ALUNOS_MATRICULADOS,
    COUNT(DISTINCT CASE WHEN R.QTD_QUESTIONARIOS > 0 THEN M.RA END) AS ALUNOS_RESPONDERAM,
    COUNT(DISTINCT CASE WHEN R.QTD_DOCENTE > 0 THEN M.RA END)       AS ALUNOS_RESP_DOCENTE,
    COUNT(DISTINCT CASE WHEN R.QTD_INSTITUCIONAL > 0 THEN M.RA END) AS ALUNOS_RESP_INSTITUCIONAL,
    SUM(ISNULL(E.AVALIACOES_ESPERADAS, 0))                          AS DOCENTE_ESPERADAS,
    SUM(ISNULL(R.QTD_DOCENTE, 0))                                   AS DOCENTE_RESPONDIDAS
FROM SMATRICPL M
INNER JOIN SPLETIVO PLM
        ON PLM.CODCOLIGADA = M.CODCOLIGADA
       AND PLM.IDPERLET = M.IDPERLET
       AND PLM.CODFILIAL = M.CODFILIAL
INNER JOIN SSTATUS ST
        ON ST.CODCOLIGADA = M.CODCOLIGADA
       AND ST.CODSTATUS = M.CODSTATUS
INNER JOIN SALUNO A
        ON A.CODCOLIGADA = M.CODCOLIGADA
       AND A.RA = M.RA
LEFT JOIN SHABILITACAOFILIAL HF
       ON HF.CODCOLIGADA = M.CODCOLIGADA
      AND HF.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
LEFT JOIN SCURSO C
       ON C.CODCOLIGADA = HF.CODCOLIGADA
      AND C.CODCURSO = HF.CODCURSO
LEFT JOIN STURMA T
       ON T.CODCOLIGADA = M.CODCOLIGADA
      AND T.CODFILIAL = M.CODFILIAL
      AND T.CODTURMA = M.CODTURMA
      AND T.IDPERLET = M.IDPERLET

-- o que este aluno respondeu no semestre (área 8 = CPA)
-- (as marcações são feitas numa tabela interna X; o SQL Server não aceita subconsulta dentro de COUNT)
OUTER APPLY (
    -- só conta questionários válidos: avaliação do curso/infraestrutura ou professor de disciplina
    -- desta matrícula (avaliação de professor de semestre anterior não conta como participação)
    SELECT COUNT(DISTINCT CASE WHEN X.E_DOCENTE_DA_MATRICULA = 1 OR X.E_INSTITUCIONAL = 1
                               THEN X.ID END)                            AS QTD_QUESTIONARIOS,
           -- cada professor/disciplina conta uma vez, mesmo que o aluno tenha avaliado duas vezes
           COUNT(DISTINCT CASE WHEN X.E_DOCENTE_DA_MATRICULA = 1 THEN X.SEQOBJETOAVALIADO END) AS QTD_DOCENTE,
           COUNT(DISTINCT CASE WHEN X.E_INSTITUCIONAL = 1 THEN X.ID END)        AS QTD_INSTITUCIONAL
    FROM (
        SELECT BH.ID,
               BH.SEQOBJETOAVALIADO,
               -- docente: só disciplinas desta matrícula
               CASE WHEN SOA.CODPROF IS NOT NULL AND SOA.IDTURMADISC IS NOT NULL
                         AND MD.IDTURMADISC IS NOT NULL THEN 1 ELSE 0 END AS E_DOCENTE_DA_MATRICULA,
               CASE WHEN SOA.CODPROF IS NULL OR SOA.IDTURMADISC IS NULL THEN 1 ELSE 0 END AS E_INSTITUCIONAL
        FROM BHISTORICO BH
        INNER JOIN BPERIODO PL
                ON PL.CODCOLIGADA = BH.CODCOLIGADA
               AND PL.CODPROVA = BH.CODPROVA
               AND PL.CODPERIODO = BH.CODPERIODO
        LEFT JOIN SOBJETOAVALIADO SOA
               ON SOA.CODCOLIGADA = BH.CODCOLIGADA
              AND SOA.SEQOBJETOAVALIADO = BH.SEQOBJETOAVALIADO
        LEFT JOIN SMATRICULA MD
               ON MD.CODCOLIGADA = M.CODCOLIGADA
              AND MD.RA = M.RA
              AND MD.IDPERLET = M.IDPERLET
              AND MD.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
              AND MD.IDTURMADISC = SOA.IDTURMADISC
        WHERE BH.CODCOLIGADA = M.CODCOLIGADA
          AND BH.CODPESSOA = A.CODPESSOA
          AND BH.CODAREA = '8'
          AND LEFT(PL.NOME, 6) = LEFT(PLM.CODPERLET, 6)
    ) X
) R

-- quantas avaliações docentes este aluno poderia ter respondido nesta matrícula
OUTER APPLY (
    SELECT COUNT(*) AS AVALIACOES_ESPERADAS
    FROM SMATRICULA MAT
    INNER JOIN SOBJETOAVALIADO SOA2
            ON SOA2.CODCOLIGADA = MAT.CODCOLIGADA
           AND SOA2.IDTURMADISC = MAT.IDTURMADISC
           AND SOA2.CODPROF IS NOT NULL
    WHERE MAT.CODCOLIGADA = M.CODCOLIGADA
      AND MAT.RA = M.RA
      AND MAT.IDPERLET = M.IDPERLET
      AND MAT.IDHABILITACAOFILIAL = M.IDHABILITACAOFILIAL
) E

WHERE M.CODCOLIGADA = 5
  AND PLM.CODPERLET IN ('2026/1', '2026/1T', '2026/2', '2026/2T')
  AND C.NOME IN ('Análise e Desenvolvimento de Sistemas', 'Direito', 'Enfermagem', 'Pedagogia', 'Psicologia', 'Teologia')
  -- só alunos ATIVOS no período: "Cursando" (semestre em andamento) ou "Concluído"
  -- (o mesmo aluno depois que o semestre encerra). Qualquer outro status fica de fora:
  -- cancelado, trancado, desvinculado, pré-matrícula (portal liberado, reserva de vaga) etc.
  AND UPPER(LTRIM(RTRIM(ST.DESCRICAO))) IN ('CURSANDO', 'CONCLUÍDO', 'CONCLUIDO')
GROUP BY PLM.CODPERLET, C.NOME, M.CODTURMA, T.NOME
ORDER BY SEMESTRE, NOME_CURSO, M.CODTURMA;
