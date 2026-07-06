"""Modelo de trafego: fluxos de demanda e aplicacao de carga nos enlaces.

Um fluxo representa uma demanda constante de banda entre uma origem e um
destino. A cada passo da simulacao, um roteador escolhe o caminho de cada
fluxo e a demanda correspondente e somada ao carregamento (load) de cada
enlace do caminho. Fluxos de fundo (background) sao usados para injetar
congestao artificial durante a demonstracao.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from . import network


@dataclass
class Flow:
    """Fluxo de trafego com demanda constante em Mbps."""
    src: str
    dst: str
    demand: float
    fid: str = ""
    is_background: bool = False
    # Caminho atribuido no ultimo passo (preenchido pelo simulador).
    path: list[str] = field(default_factory=list)
    # True quando o fluxo nao pode ser entregue (sem rota ou sem capacidade).
    dropped: bool = False


def default_flows() -> list[Flow]:
    """Conjunto de fluxos de demanda principal para a topologia de exemplo.

    O fluxo destaque e A -> D (o que sera observado no dashboard). Os demais
    fluxos criam carga de base na rede para tornar o cenario realista.
    """
    return [
        Flow("A", "D", demand=40.0, fid="A->D"),
        Flow("E", "H", demand=25.0, fid="E->H"),
        Flow("A", "H", demand=20.0, fid="A->H"),
    ]


def apply_flows(G: nx.Graph, flows: list[Flow], router,
                preload: dict | None = None) -> None:
    """Roteia cada fluxo com o `router` e acumula a carga nos enlaces.

    Zera as cargas antes de aplicar. Se `preload` for informado (mapa
    {(u, v): carga_Mbps}), essa carga e injetada nos enlaces ANTES do
    roteamento -- assim o roteador a percebe e pode desviar dela (usado
    para injetar congestao em um enlace especifico). Preenche flow.path e
    flow.dropped.
    """
    network.reset_loads(G)
    if preload:
        for (u, v), amt in preload.items():
            if G.has_edge(u, v):
                G[u][v]["load"] += amt
    for flow in flows:
        path = router.route(G, flow.src, flow.dst)
        flow.path = path or []
        if not path or len(path) < 2:
            flow.dropped = flow.src != flow.dst
            continue
        flow.dropped = False
        for a, b in zip(path, path[1:]):
            if G.has_edge(a, b):
                G[a][b]["load"] += flow.demand
    _mark_overloaded(G, flows)


def _mark_overloaded(G: nx.Graph, flows: list[Flow]) -> None:
    """Marca como dropped os fluxos que passam por enlace saturado (u > 1)."""
    for flow in flows:
        if flow.dropped or len(flow.path) < 2:
            continue
        for a, b in zip(flow.path, flow.path[1:]):
            if not G.has_edge(a, b):
                continue
            d = G[a][b]
            if d["capacity"] > 0 and d["load"] / d["capacity"] > 1.0:
                flow.dropped = True
                break


def make_background_flow(src: str, dst: str, demand: float) -> Flow:
    """Cria um fluxo de fundo (injecao de congestao)."""
    return Flow(src, dst, demand=demand, fid=f"bg:{src}->{dst}",
                is_background=True)
