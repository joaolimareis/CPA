"""Cliente da API REST do TOTVS RM (consultas SQL cadastradas no framework)."""
from __future__ import annotations

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class TotvsErro(RuntimeError):
    """Falha ao consultar a API do TOTVS."""


class TotvsClient:
    CAMINHO = "/api/framework/v1/consultaSQLServer/RealizaConsulta/{codigo}/{coligada}/{sistema}/"

    def __init__(self, base_url: str, usuario: str, senha: str,
                 timeout: int = 180, verificar_ssl: bool = True) -> None:
        if not base_url:
            raise TotvsErro("TOTVS_BASE_URL não configurada no .env")
        # Aceita tanto "https://servidor:porta" quanto a URL completa da consulta colada por engano
        self.base_url = base_url.split("/api/")[0].rstrip("/")
        self.timeout = timeout
        self.sessao = requests.Session()
        self.sessao.auth = (usuario, senha)
        self.sessao.verify = verificar_ssl
        self.sessao.headers.update({"Accept": "application/json"})
        retry = Retry(total=3, backoff_factor=2, status_forcelist=(502, 503, 504),
                      allowed_methods=("GET",))
        self.sessao.mount("https://", HTTPAdapter(max_retries=retry))
        self.sessao.mount("http://", HTTPAdapter(max_retries=retry))

    def realiza_consulta(self, codigo: str, coligada: str, sistema: str,
                         parametros: dict[str, str] | None = None) -> list[dict]:
        """Executa uma consulta SQL do RM e devolve a lista de registros."""
        url = self.base_url + self.CAMINHO.format(codigo=codigo, coligada=coligada, sistema=sistema)
        params = None
        if parametros:
            # Formato do RM: parameters=NOME1=valor1;NOME2=valor2
            params = {"parameters": ";".join(f"{k}={v}" for k, v in parametros.items())}
        logger.info("Consultando TOTVS: %s", codigo)
        try:
            resposta = self.sessao.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as erro:
            raise TotvsErro(f"Não foi possível conectar à API do TOTVS: {erro}") from erro
        if resposta.status_code == 401:
            raise TotvsErro("Usuário ou senha da API do TOTVS inválidos (HTTP 401)")
        if not resposta.ok:
            raise TotvsErro(f"API do TOTVS respondeu HTTP {resposta.status_code}: {resposta.text[:300]}")
        try:
            dados = resposta.json()
        except ValueError as erro:
            raise TotvsErro("A API do TOTVS não devolveu um JSON válido") from erro
        if not isinstance(dados, list):
            raise TotvsErro(f"Formato inesperado da API: {str(dados)[:300]}")
        logger.info("TOTVS devolveu %d registros", len(dados))
        return dados
