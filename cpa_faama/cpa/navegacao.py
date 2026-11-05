"""Páginas do sistema e quem vê cada uma (usado pelo menu e pela página inicial)."""

PAGINAS = {
    "inicio": ("views/inicio.py", "Início", "🏠"),
    "visao": ("views/visao_geral.py", "Visão Geral", "📊"),
    "docentes": ("views/docentes.py", "Avaliação Docente", "👩‍🏫"),
    "curso": ("views/curso.py", "Avaliação do Curso", "🎓"),
    "infra": ("views/infraestrutura.py", "Infraestrutura", "🏫"),
    "comentarios": ("views/comentarios.py", "Comentários", "💬"),
    "atencao": ("views/atencao.py", "Pontos de Atenção", "⚠️"),
    "ranking": ("views/ranking.py", "Participação", "🏆"),
    "historico": ("views/historico.py", "Histórico", "📈"),
    "relatorio": ("views/relatorio.py", "Relatório da CPA", "📄"),
    "metodologia": ("views/metodologia.py", "Metodologia", "📘"),
    "validacao": ("views/validacao.py", "Validação dos Dados", "✅"),
    "auditoria": ("views/auditoria.py", "Auditoria dos Dados", "🔍"),
    "admin": ("views/admin.py", "Administração", "⚙️"),
    "meu": ("views/meu_resultado.py", "Meu Resultado", "🧑‍🏫"),
}
GRUPOS_POR_PERFIL = {
    "admin": {
        "Resultados": ["inicio", "visao", "docentes", "curso", "infra", "comentarios", "atencao"],
        "Participação e histórico": ["ranking", "historico"],
        "Relatórios": ["relatorio", "metodologia"],
        "Conferência (CPA)": ["validacao", "auditoria", "admin"],
    },
    "coordenador": {
        "Resultados": ["inicio", "visao", "docentes", "curso", "infra", "comentarios", "atencao"],
        "Participação e histórico": ["ranking", "historico"],
        "Sobre": ["metodologia"],
    },
    # Avaliador externo: só visões consolidadas (sem nomes de professores e sem comentários)
    "avaliador": {
        "Resultados": ["inicio", "visao", "curso", "infra"],
        "Participação e histórico": ["ranking", "historico"],
        "Relatórios": ["relatorio", "metodologia"],
    },
    "professor": {"": ["meu"]},
}



def chaves_do_perfil(perfil: str) -> list[str]:
    return [c for chaves in GRUPOS_POR_PERFIL.get(perfil, {}).values() for c in chaves]
