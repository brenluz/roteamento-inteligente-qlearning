"""Modelo de rede: topologia em NetworkX com latencia dependente de congestao.

Cada roteador e um no. Cada enlace (aresta) possui:
    - capacity:     capacidade em Mbps
    - base_latency: latencia de propagacao/transmissao base em ms (sem fila)
    - load:         trafego agregado atual em Mbps (recalculado a cada passo)
    - up:           True se o enlace esta operacional

A latencia efetiva cresce com a utilizacao (u = load/capacity) imitando o
atraso de fila de um sistema M/M/1:

    lat_eff = base_latency * (1 + ALPHA * u**BETA)

Quando u >= CONGESTION_THRESHOLD o enlace e considerado congestionado; quando
u >= 1.0 ha perda (a demanda excede a capacidade). Enlaces com up=False sao
removidos do calculo de rotas.
"""

from __future__ import annotations

import networkx as nx

# Parametros do modelo de congestao.
ALPHA = 4.0                 # intensidade do atraso de fila
BETA = 2.0                  # curvatura (quanto mais proximo de 1.0, pior)
CONGESTION_THRESHOLD = 0.90  # utilizacao a partir da qual ha congestao
LATENCY_CAP = 50.0          # teto multiplicativo para evitar infinitos


def link_latency(base_latency: float, load: float, capacity: float) -> float:
    """Latencia efetiva de um enlace dado seu carregamento atual."""
    if capacity <= 0:
        return base_latency * LATENCY_CAP
    u = load / capacity
    factor = 1.0 + ALPHA * (u ** BETA)
    return base_latency * min(factor, LATENCY_CAP)


def is_congested(load: float, capacity: float) -> bool:
    """Retorna True se a utilizacao do enlace excede o limiar de congestao."""
    if capacity <= 0:
        return True
    return (load / capacity) >= CONGESTION_THRESHOLD


def build_topology() -> nx.Graph:
    """Constroi a topologia de exemplo com caminhos redundantes.

    Topologia (9 nos, A..I) desenhada para a demonstracao:

        A --- B --- C --- D
        |     |     |     |
        E --- F --- G --- H
               \\         /
                \\--- I -/

    O par de demanda principal e A -> D. Existe a rota curta A-B-C-D
    (que congestiona sob carga) e rotas alternativas passando pela
    fileira de baixo (A-E-F-G-H-D) e pelo no I.
    """
    G = nx.Graph()

    # (u, v, capacity_Mbps, base_latency_ms)
    edges = [
        ("A", "B", 100, 5),
        ("B", "C", 100, 5),
        ("C", "D", 100, 5),
        ("A", "E", 100, 6),
        ("B", "F", 100, 6),
        ("C", "G", 100, 6),
        ("D", "H", 100, 6),
        ("E", "F", 120, 7),
        ("F", "G", 120, 7),
        ("G", "H", 120, 7),
        ("F", "I", 150, 9),
        ("I", "H", 150, 9),
    ]

    for u, v, cap, lat in edges:
        G.add_edge(u, v, capacity=float(cap), base_latency=float(lat),
                   load=0.0, up=True)

    # Posicoes fixas para desenho consistente no dashboard (grade).
    pos = {
        "A": (0, 2), "B": (1, 2), "C": (2, 2), "D": (3, 2),
        "E": (0, 1), "F": (1, 1), "G": (2, 1), "H": (3, 1),
        "I": (2, 0),
    }
    for node, (x, y) in pos.items():
        G.nodes[node]["x"] = x
        G.nodes[node]["y"] = y

    return G


def reset_loads(G: nx.Graph) -> None:
    """Zera o carregamento de todos os enlaces (inicio de um passo)."""
    for _, _, data in G.edges(data=True):
        data["load"] = 0.0


def active_graph(G: nx.Graph) -> nx.Graph:
    """Retorna uma view apenas com enlaces operacionais (up=True).

    Usada pelos roteadores para calcular caminhos sem enlaces derrubados.
    """
    return G.edge_subgraph(
        [(u, v) for u, v, d in G.edges(data=True) if d.get("up", True)]
    ).copy()


def edge_effective_latency(G: nx.Graph, u: str, v: str) -> float:
    """Latencia efetiva do enlace (u, v) considerando sua carga atual."""
    d = G[u][v]
    if not d.get("up", True):
        return float("inf")
    return link_latency(d["base_latency"], d["load"], d["capacity"])


def path_latency(G: nx.Graph, path: list[str]) -> float:
    """Soma das latencias efetivas ao longo de um caminho.

    Retorna infinito se o caminho for invalido (enlace inexistente/derrubado).
    """
    if not path or len(path) < 2:
        return 0.0 if path else float("inf")
    total = 0.0
    for a, b in zip(path, path[1:]):
        if not G.has_edge(a, b) or not G[a][b].get("up", True):
            return float("inf")
        total += edge_effective_latency(G, a, b)
    return total


def path_min_headroom(G: nx.Graph, path: list[str]) -> float:
    """Menor folga de capacidade (capacity - load) ao longo do caminho."""
    if not path or len(path) < 2:
        return float("inf")
    hs = []
    for a, b in zip(path, path[1:]):
        if not G.has_edge(a, b):
            return float("-inf")
        d = G[a][b]
        hs.append(d["capacity"] - d["load"])
    return min(hs) if hs else float("inf")
