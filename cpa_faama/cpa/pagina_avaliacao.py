"""Página padrão das avaliações institucionais (Curso e Infraestrutura usam a mesma estrutura)."""
from __future__ import annotations

import streamlit as st

from cpa import charts, metrics, ui
from cpa.config import get_settings
from cpa.processing import PROVA_CURSO


def render(tipo_prova: str, titulo: str, subtitulo: str, chave: str, filtro_questionario: bool) -> None:
    ui.aplicar_estilo()
    df, meta = ui.base_do_usuario()
    df = df[df["TIPO_PROVA"] == tipo_prova]
    ui.cabecalho(titulo, subtitulo, meta)
    if df.empty:
        ui.sem_dados()

    campos = [("NOME_CURSO", "Curso do aluno")]
    if filtro_questionario:
        campos.append(("NOME_PROVA", "Questionário"))
    campos.append(("STATUS_MATRICULA", "Status da matrícula"))
    base = ui.filtros(df, campos, chave)
    dados, semestres = ui.filtro_semestre(base, chave)
    if dados.empty:
        ui.sem_dados()

    ind = metrics.indicadores(dados)
    ant = ui.indicadores_anteriores(base, semestres)
    ui.cartoes([
        ("Questionários respondidos", ui.num(ind.questionarios), None, "Cada questionário preenchido conta uma vez."),
        ("% Favorável", ui.pct(ind.pct_favoravel), ui.delta_pp(ind.pct_favoravel, ant and ant.pct_favoravel), None),
        ("% Neutro", ui.pct(ind.pct_neutro), None, None),
        ("% Desfavorável", ui.pct(ind.pct_desfavoravel),
         ui.delta_pp(ind.pct_desfavoravel, ant and ant.pct_desfavoravel), None),
        ("Nota média (1 a 5)", ui.num(ind.nota_media, 2), ui.delta_num(ind.nota_media, ant and ant.nota_media), None),
    ])

    minimo = get_settings().min_respondentes
    por_questao = metrics.resumo_por(dados, ["DESC_QUESTAO"])
    # Destaques: só questões objetivas com pelo menos o mínimo de respondentes. Na Avaliação do Curso,
    # cada curso tem um questionário próprio, então o destaque é feito por curso e questão.
    if tipo_prova == PROVA_CURSO:
        destaque = metrics.resumo_por(dados, ["NOME_CURSO", "DESC_QUESTAO"], minimo)
        destaque["ROTULO"] = destaque["NOME_CURSO"].astype(str) + ": " + destaque["DESC_QUESTAO"].astype(str)
    else:
        destaque = metrics.resumo_por(dados, ["DESC_QUESTAO"], minimo)
        destaque["ROTULO"] = destaque["DESC_QUESTAO"]
    destaque = destaque[(destaque["respostas_validas"] > 0) & ~destaque["protegido"]].dropna(subset=["pct_favoravel"])

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Distribuição das respostas por questão")
        if tipo_prova == PROVA_CURSO and dados["NOME_CURSO"].nunique() > 1:
            st.caption("Cada curso tem um questionário próprio. Filtre por curso para ver o questionário de um curso.")
        st.plotly_chart(charts.barras_distribuicao(metrics.distribuicao(dados, "DESC_QUESTAO"), "DESC_QUESTAO"),
                        width="stretch")
    with c2:
        st.caption(f"Destaques consideram só questões com {minimo} ou mais respondentes.")
        if destaque.empty:
            st.info(f"Ainda não há questões com {minimo} ou mais respondentes para destacar.")
        else:
            melhores = destaque.sort_values(["pct_favoravel", "questionarios"], ascending=[False, False]).head(3)
            piores = destaque[~destaque.index.isin(melhores.index)]
            piores = piores.sort_values(["pct_favoravel", "questionarios"], ascending=[True, False]).head(3)
            st.subheader("✅ Mais bem avaliados")
            for _, linha in melhores.iterrows():
                st.success(f"**{ui.pct(linha.pct_favoravel)}** · {linha.ROTULO}  \n*{int(linha.questionarios)} respondentes*")
            st.subheader("⚠️ Precisam de atenção")
            for _, linha in piores.iterrows():
                st.error(f"**{ui.pct(linha.pct_favoravel)}** · {linha.ROTULO}  \n*{int(linha.questionarios)} respondentes*")

    por_curso = metrics.resumo_por(dados, ["NOME_CURSO"], minimo)
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("% favorável por curso do aluno")
        st.plotly_chart(charts.barras_percentual(por_curso, "NOME_CURSO"), width="stretch")
    with c4:
        st.subheader("Questionários por curso do aluno")
        st.plotly_chart(charts.barras_quantidade(por_curso, "NOME_CURSO"), width="stretch")

    st.caption(f"Cursos com menos de {minimo} respondentes aparecem sem resultado nos gráficos por curso.")
    st.subheader("% favorável: curso do aluno × questão")
    st.plotly_chart(charts.mapa_calor(metrics.mapa_calor(dados, "NOME_CURSO", "DESC_QUESTAO", minimo)), width="stretch")

    ui.botao_excel({"Por questão": por_questao, "Por curso": por_curso,
                    "Curso x questão": metrics.resumo_por(dados, ["NOME_CURSO", "DESC_QUESTAO"])},
                   f"cpa_{chave}.xlsx", f"xls_{chave}")
    ui.nota_sigilo()
