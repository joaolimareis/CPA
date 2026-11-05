"""Busca os dados (API ou demonstração), trata e guarda uma cópia local.

Se a API do TOTVS estiver fora do ar, o sistema continua funcionando com a última cópia.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta

import pandas as pd

from cpa import demo, participacao
from cpa.config import get_settings
from cpa.processing import processar
from cpa.totvs_client import TotvsClient

logger = logging.getLogger(__name__)

ARQUIVO_BASE = "respostas.parquet"
ARQUIVO_META = "atualizacao.json"
VERSAO_BASE = 6
ARQUIVO_DESCARTES = "descartes.parquet"  # muda quando o tratamento muda; força reprocessar a cópia local


def _buscar_registros() -> tuple[list[dict], str]:
    s = get_settings()
    if s.modo_demo:
        return demo.gerar(), "Demonstração (dados fictícios)"
    cliente = TotvsClient(s.totvs_base_url, s.totvs_usuario, s.totvs_senha,
                          s.totvs_timeout, s.totvs_verificar_ssl)
    registros = cliente.realiza_consulta(s.totvs_consulta, s.totvs_coligada, s.totvs_sistema)
    return registros, f"API TOTVS ({s.totvs_consulta})"


def _ler_copia() -> tuple[pd.DataFrame, dict] | None:
    pasta = get_settings().pasta_dados
    base, meta = pasta / ARQUIVO_BASE, pasta / ARQUIVO_META
    if not (base.exists() and meta.exists()):
        return None
    return pd.read_parquet(base), json.loads(meta.read_text(encoding="utf-8"))


def _salvar_copia(df: pd.DataFrame, meta: dict) -> None:
    pasta = get_settings().pasta_dados
    pasta.mkdir(parents=True, exist_ok=True)
    temporario = pasta / (ARQUIVO_BASE + ".tmp")
    df.to_parquet(temporario, index=False)
    os.replace(temporario, pasta / ARQUIVO_BASE)  # troca atômica: nunca deixa arquivo pela metade
    (pasta / ARQUIVO_META).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _salvar_descartes(df: pd.DataFrame) -> None:
    pasta = get_settings().pasta_dados
    pasta.mkdir(parents=True, exist_ok=True)
    temporario = pasta / (ARQUIVO_DESCARTES + ".tmp")
    df.to_parquet(temporario, index=False)
    os.replace(temporario, pasta / ARQUIVO_DESCARTES)


def carregar_descartes() -> pd.DataFrame:
    """Avaliações docentes descartadas (professor de semestre anterior ou repetida), com o motivo."""
    caminho = get_settings().pasta_dados / ARQUIVO_DESCARTES
    return pd.read_parquet(caminho) if caminho.exists() else pd.DataFrame()


def carregar_base(forcar: bool = False) -> tuple[pd.DataFrame, dict]:
    """Devolve (base tratada, metadados da atualização)."""
    s = get_settings()
    copia = _ler_copia()
    if copia and not forcar:
        df, meta = copia
        atualizado = datetime.fromisoformat(meta["atualizado_em"])
        mesma_origem = meta.get("modo_demo") == s.modo_demo and meta.get("versao") == VERSAO_BASE
        if mesma_origem and datetime.now() - atualizado < timedelta(minutes=s.cache_minutos):
            return df, meta

    try:
        registros, origem = _buscar_registros()
        relatorio: dict = {}
        descartes: list = []
        df = processar(registros, s.cursos_excluidos, s.provas_infraestrutura, s.palavra_prova_infra, relatorio,
                       cursos_permitidos=s.cursos_permitidos, descartes=descartes,
                       questoes_anuladas=s.questoes_anuladas)
        _salvar_descartes(pd.concat(descartes, ignore_index=True) if descartes else pd.DataFrame())
        meta = {
            "origem": origem,
            "modo_demo": s.modo_demo,
            "versao": VERSAO_BASE,
            "atualizado_em": datetime.now().isoformat(timespec="seconds"),
            "linhas_api": len(registros),
            "linhas_tratadas": len(df),
            "relatorio": relatorio,
            "tem_data_resposta": "DATA_RESPOSTA" in df.columns,
        }
        _salvar_copia(df, meta)
        return df, meta
    except Exception as erro:  # noqa: BLE001 - qualquer falha cai para a cópia local
        logger.exception("Falha ao atualizar os dados")
        # Só usa a cópia salva se ela for da mesma origem (nunca mostra dado fictício no lugar do real)
        if copia and copia[1].get("modo_demo") == s.modo_demo and copia[1].get("versao") == VERSAO_BASE:
            df, meta = copia
            meta = dict(meta, aviso=f"Não foi possível atualizar agora ({erro}). Exibindo a última cópia salva.")
            return df, meta
        raise


# ---------- participação (consulta agregada por turma) ----------

ARQUIVO_PART = "participacao.parquet"
ARQUIVO_PART_META = "participacao.json"


def participacao_configurada() -> bool:
    s = get_settings()
    return s.modo_demo or bool(s.totvs_consulta_participacao)


def carregar_participacao(forcar: bool = False) -> tuple[pd.DataFrame, dict]:
    s = get_settings()
    pasta = s.pasta_dados
    base, meta_path = pasta / ARQUIVO_PART, pasta / ARQUIVO_PART_META
    copia = None
    if base.exists() and meta_path.exists():
        copia = pd.read_parquet(base), json.loads(meta_path.read_text(encoding="utf-8"))
        df, meta = copia
        idade = datetime.now() - datetime.fromisoformat(meta["atualizado_em"])
        if not forcar and meta.get("modo_demo") == s.modo_demo and idade < timedelta(minutes=s.cache_minutos):
            return df, meta
    try:
        if s.modo_demo:
            registros, origem = participacao.gerar_demo(), "Demonstração (dados fictícios)"
        else:
            cliente = TotvsClient(s.totvs_base_url, s.totvs_usuario, s.totvs_senha,
                                  s.totvs_timeout, s.totvs_verificar_ssl)
            registros = cliente.realiza_consulta(s.totvs_consulta_participacao, s.totvs_coligada, s.totvs_sistema)
            origem = f"API TOTVS ({s.totvs_consulta_participacao})"
        df = participacao.processar(registros)
        if s.cursos_permitidos:
            df = df[df["NOME_CURSO"].isin(s.cursos_permitidos)].reset_index(drop=True)
        meta = {"origem": origem, "modo_demo": s.modo_demo,
                "atualizado_em": datetime.now().isoformat(timespec="seconds")}
        pasta.mkdir(parents=True, exist_ok=True)
        temporario = pasta / (ARQUIVO_PART + ".tmp")
        df.to_parquet(temporario, index=False)
        os.replace(temporario, base)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return df, meta
    except Exception as erro:  # noqa: BLE001
        logger.exception("Falha ao atualizar a participação")
        if copia and copia[1].get("modo_demo") == s.modo_demo:
            return copia[0], dict(copia[1], aviso=f"Não foi possível atualizar agora ({erro}). Exibindo a última cópia.")
        raise
