"""Motor de simulacao por passos.

Mantem o estado do "mundo" (topologia, enlaces up/down e congestao injetada) e,
a cada passo, avalia OS DOIS roteadores nas MESMAS condicoes, produzindo:

    - o carregamento de cada enlace sob cada roteador,
    - o caminho de cada fluxo sob cada roteador,
    - as metricas comparativas.

O agente Q-Learning treina alguns episodios por passo sobre o estado atual
(com a congestao vigente), o que faz sua politica se adaptar ao longo do tempo.
Eventos (derrubar/restaurar enlace, injetar congestao, reset) alteram o mundo
em tempo real -- sao os gatilhos da demonstracao.
"""

from __future__ import annotations

import copy
import threading

import networkx as nx

from . import metrics as metrics_mod
from . import network, traffic
from .routers.dijkstra_router import DijkstraRouter
from .routers.qlearning_router import QLearningRouter


class Simulator:
    def __init__(self, highlight: str = "A->D", warmup_episodes: int = 4000):
        self.G = network.build_topology()
        self.flows = traffic.default_flows()
        self.highlight = highlight  # fluxo destacado na visualizacao

        # Congestao injetada: {(u, v): carga_extra_Mbps}.
        self.injected: dict[tuple[str, str], float] = {}

        self.dijkstra = DijkstraRouter()
        # O agente foca nos destinos dos fluxos de demanda + todos os nos.
        dests = sorted({f.dst for f in self.flows})
        self.qlearning = QLearningRouter(destinations=None, episodes_per_step=300)
        self.qlearning.warmup(self.G, episodes=warmup_episodes)

        self.step_count = 0
        self.lock = threading.Lock()
        # Resultado da ultima avaliacao (para serializacao no dashboard).
        self._last = {"dijkstra": None, "qlearning": None}
        self._history: list[dict] = []
        self.step()  # avalia estado inicial

    # ------------------------------------------------------------------ passos
    def _evaluate(self, router) -> tuple[nx.Graph, list[traffic.Flow], metrics_mod.Metrics]:
        """Avalia um roteador numa copia do grafo (nao contamina o outro)."""
        G = self.G.copy()
        flows = [copy.copy(f) for f in self.flows]
        traffic.apply_flows(G, flows, router, preload=self.injected)
        m = metrics_mod.compute(G, flows)
        return G, flows, m

    def step(self) -> None:
        """Avanca um passo: avalia os dois roteadores e treina o agente."""
        with self.lock:
            self.step_count += 1

            Gd, flows_d, md = self._evaluate(self.dijkstra)
            Gq, flows_q, mq = self._evaluate(self.qlearning)

            # O agente aprende sobre a congestao que ele mesmo enfrenta.
            self.qlearning.on_step(Gq)

            self._last = {
                "dijkstra": (Gd, flows_d, md),
                "qlearning": (Gq, flows_q, mq),
            }
            self._history.append({
                "step": self.step_count,
                "dijkstra": round(md.penalized_latency, 2),
                "qlearning": round(mq.penalized_latency, 2),
            })
            if len(self._history) > 200:
                self._history = self._history[-200:]

    # ------------------------------------------------------------------ eventos
    def drop_link(self, u: str, v: str) -> bool:
        with self.lock:
            if self.G.has_edge(u, v):
                self.G[u][v]["up"] = False
                self.injected.pop((u, v), None)
                self.injected.pop((v, u), None)
                return True
        return False

    def restore_link(self, u: str, v: str) -> bool:
        """Restaura o enlace a condicao inicial: sobe e limpa a congestao."""
        with self.lock:
            if self.G.has_edge(u, v):
                self.G[u][v]["up"] = True
                self.injected.pop((u, v), None)
                self.injected.pop((v, u), None)
                return True
        return False

    def congest(self, u: str, v: str, amount: float | None = None) -> bool:
        """Injeta carga num enlace ate leva-lo a congestionar."""
        with self.lock:
            if not self.G.has_edge(u, v):
                return False
            cap = self.G[u][v]["capacity"]
            self.injected[(u, v)] = amount if amount is not None else cap * 0.95
            return True

    def restore_all(self) -> None:
        with self.lock:
            self.injected.clear()
            for _, _, d in self.G.edges(data=True):
                d["up"] = True

    def reset(self) -> None:
        with self.lock:
            self.G = network.build_topology()
            self.injected.clear()
            self._history.clear()
            self.step_count = 0

    def set_highlight(self, flow_id: str) -> None:
        with self.lock:
            self.highlight = flow_id

    # -------------------------------------------------------------- serializacao
    def _highlight_flow(self, flows: list[traffic.Flow]) -> traffic.Flow | None:
        for f in flows:
            if f.fid == self.highlight:
                return f
        return flows[0] if flows else None

    def state(self) -> dict:
        """Snapshot serializavel para o dashboard."""
        with self.lock:
            Gd, flows_d, md = self._last["dijkstra"]
            Gq, flows_q, mq = self._last["qlearning"]

            nodes = [
                {"id": n, "x": d.get("x", 0), "y": d.get("y", 0)}
                for n, d in self.G.nodes(data=True)
            ]

            edges = []
            for u, v, d in self.G.edges(data=True):
                cap = d["capacity"]
                load_d = Gd[u][v]["load"] if Gd.has_edge(u, v) else 0.0
                load_q = Gq[u][v]["load"] if Gq.has_edge(u, v) else 0.0
                edges.append({
                    "source": u, "target": v,
                    "capacity": cap,
                    "base_latency": d["base_latency"],
                    "up": d.get("up", True),
                    "util_dijkstra": round(load_d / cap, 3) if cap else 0,
                    "util_qlearning": round(load_q / cap, 3) if cap else 0,
                    "injected": (u, v) in self.injected or (v, u) in self.injected,
                })

            fd = self._highlight_flow(flows_d)
            fq = self._highlight_flow(flows_q)
            paths = {
                "dijkstra": fd.path if fd else [],
                "qlearning": fq.path if fq else [],
            }

            return {
                "step": self.step_count,
                "nodes": nodes,
                "edges": edges,
                "paths": paths,
                "highlight": self.highlight,
                "flows": [f.fid for f in self.flows],
                "metrics": {
                    "dijkstra": md.as_dict(),
                    "qlearning": mq.as_dict(),
                },
                "history": self._history[-60:],
            }
