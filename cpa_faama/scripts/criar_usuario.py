"""Cria ou altera usuários do sistema.

Exemplos:
  python scripts/criar_usuario.py cpa --nome "Comissão Própria de Avaliação" --perfil admin
  python scripts/criar_usuario.py coord.direito --nome "Coordenação de Direito" --perfil coordenador --cursos "Direito"
  python scripts/criar_usuario.py prof.maria --nome "Maria Souza" --perfil professor --codprof 01234
  python scripts/criar_usuario.py mec.avaliador1 --nome "Avaliador MEC" --perfil avaliador --validade 2026-12-15
  python scripts/criar_usuario.py prof.maria --desativar
"""
import argparse
import getpass
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cpa.auth import PERFIS, gerar_hash  # noqa: E402
from cpa.config import get_settings  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Cria ou altera usuários do sistema da CPA")
    p.add_argument("login")
    p.add_argument("--nome")
    p.add_argument("--perfil", choices=sorted(PERFIS))
    p.add_argument("--cursos", help="Para coordenador: nomes dos cursos separados por ';' (igual ao TOTVS)")
    p.add_argument("--codprof", help="Para professor: código do professor no TOTVS (CODPROF)")
    p.add_argument("--validade", help="Data final de acesso (AAAA-MM-DD), recomendada para avaliadores externos")
    p.add_argument("--desativar", action="store_true")
    p.add_argument("--sem-senha", action="store_true", help="Altera dados sem trocar a senha")
    a = p.parse_args()

    caminho = get_settings().arquivo_usuarios
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = yaml.safe_load(caminho.read_text(encoding="utf-8")) if caminho.exists() else None
    conteudo = conteudo or {}
    usuarios = conteudo.setdefault("usuarios", {}) or {}
    conteudo["usuarios"] = usuarios
    login = a.login.strip().lower()
    dados = usuarios.get(login, {})

    if a.desativar:
        if not dados:
            sys.exit(f"Usuário '{login}' não existe.")
        dados["ativo"] = False
    else:
        perfil = a.perfil or dados.get("perfil")
        if not perfil:
            sys.exit("Informe --perfil para um usuário novo.")
        if perfil == "coordenador" and not (a.cursos or dados.get("cursos")):
            sys.exit("Coordenador precisa de --cursos.")
        if perfil == "professor" and not (a.codprof or dados.get("codprof")):
            sys.exit("Professor precisa de --codprof.")
        dados.update({"nome": a.nome or dados.get("nome", login), "perfil": perfil, "ativo": True})
        if a.cursos:
            dados["cursos"] = [c.strip() for c in a.cursos.split(";") if c.strip()]
        if a.codprof:
            dados["codprof"] = a.codprof.strip()
        if a.validade:
            from datetime import date
            try:
                date.fromisoformat(a.validade)
            except ValueError:
                sys.exit("Use a data no formato AAAA-MM-DD, por exemplo 2026-12-15.")
            dados["valido_ate"] = a.validade
        if perfil == "avaliador" and not dados.get("valido_ate"):
            print("Atenção: avaliador externo sem --validade. Recomenda-se definir uma data final de acesso.")
        if not (a.sem_senha and dados.get("senha_hash")):
            senha = getpass.getpass(f"Senha para {login}: ")
            if len(senha) < 8:
                sys.exit("A senha precisa ter pelo menos 8 caracteres.")
            if senha != getpass.getpass("Repita a senha: "):
                sys.exit("As senhas não conferem.")
            dados["senha_hash"] = gerar_hash(senha)

    usuarios[login] = dados
    caminho.write_text(yaml.safe_dump(conteudo, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Usuário '{login}' salvo em {caminho}.")


if __name__ == "__main__":
    main()
