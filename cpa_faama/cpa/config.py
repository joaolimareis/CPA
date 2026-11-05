"""Configurações do sistema, lidas do arquivo .env (ou de variáveis de ambiente)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent


def _bool(valor: str | None, padrao: bool = False) -> bool:
    if valor is None or valor.strip() == "":
        return padrao
    return valor.strip().lower() in {"1", "true", "sim", "yes", "on"}


def _lista(valor: str | None) -> tuple[str, ...]:
    if not valor:
        return ()
    return tuple(item.strip() for item in valor.split(";") if item.strip())


@dataclass(frozen=True)
class Settings:
    # API TOTVS RM
    totvs_base_url: str
    totvs_usuario: str
    totvs_senha: str
    totvs_consulta: str
    totvs_consulta_participacao: str
    totvs_coligada: str
    totvs_sistema: str
    totvs_timeout: int
    totvs_verificar_ssl: bool
    # Comportamento
    modo_demo: bool
    cache_minutos: int
    min_respondentes: int
    cursos_excluidos: tuple[str, ...]
    cursos_permitidos: tuple[str, ...]
    questoes_anuladas: tuple[str, ...]
    provas_infraestrutura: tuple[str, ...]
    palavra_prova_infra: str
    nome_instituicao: str
    prazo_avaliacao: str
    sessao_minutos: int
    # Arquivos
    arquivo_usuarios: Path
    arquivo_moderacao: Path
    pasta_dados: Path


@lru_cache
def get_settings() -> Settings:
    load_dotenv(RAIZ / ".env")
    base_url = os.getenv("TOTVS_BASE_URL", "").rstrip("/")
    return Settings(
        totvs_base_url=base_url,
        totvs_usuario=os.getenv("TOTVS_USUARIO", ""),
        totvs_senha=os.getenv("TOTVS_SENHA", ""),
        totvs_consulta=os.getenv("TOTVS_CONSULTA", "FAAMACPA.6"),
        totvs_consulta_participacao=os.getenv("TOTVS_CONSULTA_PARTICIPACAO", ""),
        totvs_coligada=os.getenv("TOTVS_COLIGADA", "5"),
        totvs_sistema=os.getenv("TOTVS_SISTEMA", "S"),
        totvs_timeout=int(os.getenv("TOTVS_TIMEOUT", "180")),
        totvs_verificar_ssl=_bool(os.getenv("TOTVS_VERIFICAR_SSL"), True),
        # Sem URL configurada, o sistema sobe com dados fictícios
        modo_demo=_bool(os.getenv("MODO_DEMO"), padrao=not base_url),
        cache_minutos=int(os.getenv("CACHE_MINUTOS", "60")),
        min_respondentes=int(os.getenv("MIN_RESPONDENTES", "5")),
        cursos_excluidos=_lista(os.getenv("CURSOS_EXCLUIDOS")),
        cursos_permitidos=_lista(os.getenv("CURSOS_PERMITIDOS")),
        # prova:matéria:questão aplicadas por engano (padrão: questões do Direito na prova 31 da Psicologia)
        questoes_anuladas=_lista(os.getenv("QUESTOES_ANULADAS", "31:2:15;31:2:16")),
        provas_infraestrutura=_lista(os.getenv("PROVAS_INFRAESTRUTURA")),
        palavra_prova_infra=os.getenv("PALAVRA_PROVA_INFRA", "Infraestrutura"),
        nome_instituicao=os.getenv("NOME_INSTITUICAO", "FAAMA"),
        prazo_avaliacao=os.getenv("PRAZO_AVALIACAO", ""),          # ex.: 2026-11-15 (mostra os dias restantes)
        sessao_minutos=int(os.getenv("SESSAO_MINUTOS", "60")),     # sai sozinho após X minutos sem uso
        arquivo_usuarios=RAIZ / os.getenv("ARQUIVO_USUARIOS", "config/usuarios.yaml"),
        arquivo_moderacao=RAIZ / os.getenv("ARQUIVO_MODERACAO", "config/moderacao.yaml"),
        pasta_dados=RAIZ / os.getenv("PASTA_DADOS", "data"),
    )
