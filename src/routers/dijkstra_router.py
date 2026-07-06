"""Roteador baseline: Dijkstra estatico (estilo OSPF).

Calcula o caminho mais curto usando como peso a latencia BASE dos enlaces
(latencia de propagacao, independente da carga). Este e o comportamento
classico: o custo do enlace e fixo e so muda quando a topologia muda
(um enlace cai). Consequentemente, o roteador NAO reage a congestionamento
em tempo real -- exatamente a limitacao que o agente inteligente supera.
"""

from __future__ import annotations

import networkx as nx

from .. import network
from .base import Router


class DijkstraRouter(Router):
    name = "dijkstra"

    def route(self, G: nx.Graph, src: str, dst: str) -> list[str]:
        if src == dst:
            return [src]
        active = network.active_graph(G)
        if src not in active or dst not in active:
            return []
        try:
            # Peso = latencia base (fixa). Ignora 'load'/congestao.
            return nx.shortest_path(active, src, dst, weight="base_latency")
        except nx.NetworkXNoPath:
            return []
