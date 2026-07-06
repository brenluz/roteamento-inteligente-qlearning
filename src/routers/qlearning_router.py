"""Agente de roteamento por Q-Learning (aprendizado por reforco tabular).

Formulacao
----------
O roteamento e modelado como um problema de decisao sequencial, uma tabela Q
por destino:

    estado  = no atual da rede
    acao    = escolher um vizinho como proximo salto
    recompensa = - (latencia efetiva do enlace usado)   [quanto menor, melhor]
                 - PENALIDADE_CONGESTAO  se o enlace estiver congestionado
                 - PENALIDADE_PASSO      (incentiva caminhos curtos)
    terminal = chegar ao destino  (recompensa BONUS_DESTINO)

Atualizacao (Q-learning off-policy):

    Q(s,a) <- Q(s,a) + lr * ( r + gamma * max_a' Q(s',a')  -  Q(s,a) )

Exploracao epsilon-gulosa. Como a recompensa usa a latencia EFETIVA (que cresce
com a carga do enlace), quando um enlace congestiona ou cai as recompensas
mudam e, apos alguns episodios de treino, a politica passa a desviar o trafego
-- e isso que produz o reroteamento adaptativo visivel na demonstracao.

O metodo route() segue a politica gulosa (argmax Q) salto a salto. Ha
salvaguardas contra lacos (limite de saltos, deteccao de no repetido) e, se o
agente nao alcancar o destino, ha um fallback para o caminho mais curto por
latencia base (garante conectividade mesmo antes da convergencia).
"""

from __future__ import annotations

import random
from collections import defaultdict

import networkx as nx

from .. import network
from .base import Router

# Hiperparametros do Q-Learning.
LEARNING_RATE = 0.5
GAMMA = 0.9
EPSILON = 0.2                 # taxa de exploracao durante o treino
PENALIDADE_CONGESTAO = 200.0  # custo extra por usar enlace congestionado
PENALIDADE_PASSO = 2.0        # custo fixo por salto (favorece rotas curtas)
BONUS_DESTINO = 50.0          # recompensa ao alcancar o destino


class QLearningRouter(Router):
    name = "qlearning"

    def __init__(self, seed: int | None = 42,
                 episodes_per_step: int = 300,
                 destinations: list[str] | None = None):
        self.rng = random.Random(seed)
        self.episodes_per_step = episodes_per_step
        self.destinations = destinations  # None = todos os nos
        # Q[dst][no][vizinho] -> valor.
        self.Q: dict[str, dict[str, dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float)))
        self._nodes: list[str] = []

    # ------------------------------------------------------------------ treino
    def warmup(self, G: nx.Graph, episodes: int = 4000) -> None:
        """Treino inicial intenso para partir de uma politica razoavel."""
        self._nodes = list(G.nodes())
        dests = self.destinations or self._nodes
        for _ in range(episodes):
            dst = self.rng.choice(dests)
            self._run_episode(G, dst)

    def on_step(self, G: nx.Graph) -> None:
        """Treina alguns episodios sobre o estado ATUAL da rede (com cargas)."""
        self._nodes = list(G.nodes())
        dests = self.destinations or self._nodes
        for _ in range(self.episodes_per_step):
            dst = self.rng.choice(dests)
            self._run_episode(G, dst)

    def _neighbors(self, G: nx.Graph, node: str) -> list[str]:
        """Vizinhos alcancaveis por enlaces operacionais (up=True)."""
        out = []
        for nb in G.neighbors(node):
            if G[node][nb].get("up", True):
                out.append(nb)
        return out

    def _run_episode(self, G: nx.Graph, dst: str) -> None:
        """Um episodio de aprendizado terminando (ou nao) em `dst`."""
        node = self.rng.choice(self._nodes)
        max_hops = 3 * len(self._nodes)
        qd = self.Q[dst]

        for _ in range(max_hops):
            if node == dst:
                return
            neighbors = self._neighbors(G, node)
            if not neighbors:
                return

            # Escolha epsilon-gulosa da acao (proximo salto).
            if self.rng.random() < EPSILON:
                action = self.rng.choice(neighbors)
            else:
                action = self._best_action(qd, node, neighbors)

            # Recompensa imediata.
            d = G[node][action]
            lat = network.link_latency(d["base_latency"], d["load"],
                                       d["capacity"])
            reward = -lat - PENALIDADE_PASSO
            if network.is_congested(d["load"], d["capacity"]):
                reward -= PENALIDADE_CONGESTAO

            # Alvo do Q-learning.
            if action == dst:
                reward += BONUS_DESTINO
                target = reward
            else:
                nxt_neighbors = self._neighbors(G, action)
                best_next = max(
                    (qd[action][n] for n in nxt_neighbors), default=0.0)
                target = reward + GAMMA * best_next

            qd[node][action] += LEARNING_RATE * (target - qd[node][action])
            node = action

    def _best_action(self, qd, node, neighbors: list[str]) -> str:
        """Acao de maior valor Q (desempate aleatorio)."""
        best_val = max(qd[node][n] for n in neighbors)
        best = [n for n in neighbors if qd[node][n] == best_val]
        return self.rng.choice(best)

    # ---------------------------------------------------------------- inferencia
    def route(self, G: nx.Graph, src: str, dst: str) -> list[str]:
        """Segue a politica gulosa de src ate dst, com salvaguardas."""
        if src == dst:
            return [src]
        if not self._nodes:
            self._nodes = list(G.nodes())

        qd = self.Q[dst]
        path = [src]
        visited = {src}
        node = src
        max_hops = 3 * len(self._nodes)

        for _ in range(max_hops):
            neighbors = self._neighbors(G, node)
            if not neighbors:
                break
            # Prefere vizinhos ainda nao visitados (evita laco).
            candidates = [n for n in neighbors if n not in visited] or neighbors
            action = self._best_action(qd, node, candidates)
            path.append(action)
            if action == dst:
                return path
            if action in visited:  # laco detectado
                break
            visited.add(action)
            node = action

        # Fallback: agente ainda nao converge -> caminho mais curto base.
        return self._fallback(G, src, dst)

    def _fallback(self, G: nx.Graph, src: str, dst: str) -> list[str]:
        active = network.active_graph(G)
        if src not in active or dst not in active:
            return []
        try:
            return nx.shortest_path(active, src, dst, weight="base_latency")
        except nx.NetworkXNoPath:
            return []
