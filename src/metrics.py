"""Coleta de metricas de desempenho de roteamento.

As metricas sao calculadas sobre o estado atual do grafo (com cargas ja
aplicadas) e o conjunto de fluxos roteados. Permitem comparar objetivamente o
baseline (Dijkstra) com o agente (Q-Learning) nas mesmas condicoes.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from . import network


# Penalidade (ms) atribuida a cada fluxo descartado, para que descartar
# trafego NAO "melhore" artificialmente a latencia media observada.
DROP_PENALTY_MS = 500.0


@dataclass
class Metrics:
    avg_latency: float          # latencia fim-a-fim media dos fluxos ENTREGUES (ms)
    penalized_latency: float    # media incluindo penalidade por descarte (ms)
    worst_latency: float        # pior latencia entre os fluxos (ms)
    max_utilization: float      # utilizacao maxima entre os enlaces (0..1+)
    congested_links: int        # numero de enlaces congestionados
    dropped_flows: int          # fluxos sem entrega (sem rota / saturados)
    delivered_flows: int        # fluxos entregues

    def as_dict(self) -> dict:
        return {
            "avg_latency": round(self.avg_latency, 2),
            "penalized_latency": round(self.penalized_latency, 2),
            "worst_latency": round(self.worst_latency, 2),
            "max_utilization": round(self.max_utilization, 3),
            "congested_links": self.congested_links,
            "dropped_flows": self.dropped_flows,
            "delivered_flows": self.delivered_flows,
        }


def compute(G: nx.Graph, flows) -> Metrics:
    """Calcula as metricas para o estado atual do grafo e dos fluxos."""
    latencies = []
    dropped = 0
    delivered = 0
    for flow in flows:
        if flow.is_background:
            continue
        if flow.dropped or len(flow.path) < 2:
            dropped += 1
            continue
        lat = network.path_latency(G, flow.path)
        if lat == float("inf"):
            dropped += 1
            continue
        latencies.append(lat)
        delivered += 1

    max_util = 0.0
    congested = 0
    for _, _, d in G.edges(data=True):
        if not d.get("up", True):
            continue
        if d["capacity"] > 0:
            u = d["load"] / d["capacity"]
            max_util = max(max_util, u)
            if u >= network.CONGESTION_THRESHOLD:
                congested += 1

    avg = sum(latencies) / len(latencies) if latencies else 0.0
    worst = max(latencies) if latencies else 0.0

    total_flows = delivered + dropped
    if total_flows > 0:
        penalized = (sum(latencies) + dropped * DROP_PENALTY_MS) / total_flows
    else:
        penalized = 0.0

    return Metrics(avg, penalized, worst, max_util, congested, dropped,
                   delivered)
