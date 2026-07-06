"""Interface comum dos roteadores."""

from __future__ import annotations

import networkx as nx


class Router:
    """Contrato de um roteador.

    route(): dado o grafo (com cargas atuais) e um par origem/destino,
             retorna o caminho como lista de nos. Lista vazia = sem rota.
    on_step(): gancho chamado a cada passo da simulacao. Roteadores
             estaticos ignoram; agentes que aprendem usam para treinar.
    """

    name: str = "base"

    def route(self, G: nx.Graph, src: str, dst: str) -> list[str]:
        raise NotImplementedError

    def on_step(self, G: nx.Graph) -> None:
        """Hook opcional de aprendizado/adaptacao por passo."""
        return None
