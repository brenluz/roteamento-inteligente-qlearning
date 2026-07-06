"""Experimentos comparativos headless: Dijkstra estatico x agente Q-Learning.

Executa tres cenarios nas MESMAS condicoes para os dois roteadores, registra a
evolucao das metricas passo a passo e gera:

    results/cenario2_congestao.png   - latencia ao longo do tempo (congestao)
    results/cenario3_falha.png       - latencia ao longo do tempo (falha de enlace)
    results/comparacao_barras.png    - barras resumo dos tres cenarios
    results/resultados.csv           - tabela consolidada

Uso:
    python experiments/run_experiments.py
"""

from __future__ import annotations

import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")  # backend sem janela (salva arquivos)
import matplotlib.pyplot as plt  # noqa: E402

# Permite `python experiments/run_experiments.py` a partir da raiz do projeto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulator import Simulator  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
COL_DIJKSTRA = "#d9534f"   # vermelho
COL_QLEARNING = "#0275d8"  # azul


def _new_sim() -> Simulator:
    # Warmup alto para o agente partir ja convergido no cenario sem falhas.
    return Simulator(warmup_episodes=6000)


def _run(sim: Simulator, steps: int) -> None:
    for _ in range(steps):
        sim.step()


def _series(sim: Simulator) -> tuple[list[int], list[float], list[float]]:
    steps = [h["step"] for h in sim._history]
    dj = [h["dijkstra"] for h in sim._history]
    ql = [h["qlearning"] for h in sim._history]
    return steps, dj, ql


def _snapshot(sim: Simulator) -> dict:
    st = sim.state()
    return {"dijkstra": st["metrics"]["dijkstra"],
            "qlearning": st["metrics"]["qlearning"]}


def cenario1_baseline() -> dict:
    """Rede sem congestao nem falhas: os dois devem ter desempenho similar."""
    sim = _new_sim()
    _run(sim, 30)
    snap = _snapshot(sim)
    print("\n[Cenario 1] Baseline (sem congestao/falha)")
    _print_snap(snap)
    return snap


def cenario2_congestao():
    """Congestao injetada no enlace B-C (rota curta de A->D)."""
    sim = _new_sim()
    _run(sim, 15)                 # estabiliza
    sim.congest("B", "C")         # injeta congestao ao vivo
    _run(sim, 40)                 # agente reage/aprende a desviar
    steps, dj, ql = _series(sim)
    snap = _snapshot(sim)
    print("\n[Cenario 2] Congestao no enlace B-C")
    _print_snap(snap)

    plt.figure(figsize=(8, 4.5))
    plt.axvline(15, color="gray", ls="--", lw=1, label="injecao de congestao")
    plt.plot(steps, dj, color=COL_DIJKSTRA, lw=2, label="Dijkstra (estatico)")
    plt.plot(steps, ql, color=COL_QLEARNING, lw=2, label="Q-Learning (agente)")
    plt.xlabel("Passo da simulacao")
    plt.ylabel("Latencia media penalizada (ms)")
    plt.title("Cenario 2 - Congestao no enlace B-C")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    _save("cenario2_congestao.png")
    return snap


def cenario3_falha():
    """Falha do enlace C-D que concentra trafego e congestiona o gargalo G-H.

    O Dijkstra reconverge apos a falha (reage a topologia), mas funila todos os
    fluxos no gargalo G-H sem perceber a congestao resultante e satura o enlace.
    O agente Q-Learning percebe o gargalo e desvia pelo caminho alternativo via
    no I (A-E-F-I-H-D).
    """
    sim = _new_sim()
    _run(sim, 15)
    sim.drop_link("C", "D")       # derruba enlace principal ao vivo
    sim.congest("G", "H")         # concentracao de trafego no gargalo
    _run(sim, 45)
    steps, dj, ql = _series(sim)
    snap = _snapshot(sim)
    print("\n[Cenario 3] Falha de C-D + congestao no gargalo G-H")
    _print_snap(snap)

    plt.figure(figsize=(8, 4.5))
    plt.axvline(15, color="gray", ls="--", lw=1, label="falha C-D + gargalo G-H")
    plt.plot(steps, dj, color=COL_DIJKSTRA, lw=2, label="Dijkstra (estatico)")
    plt.plot(steps, ql, color=COL_QLEARNING, lw=2, label="Q-Learning (agente)")
    plt.xlabel("Passo da simulacao")
    plt.ylabel("Latencia media penalizada (ms)")
    plt.title("Cenario 3 - Falha de C-D com congestao no gargalo")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    _save("cenario3_falha.png")
    return snap


def grafico_barras(s1: dict, s2: dict, s3: dict) -> None:
    """Barras comparando a latencia penalizada nos tres cenarios."""
    cenarios = ["Baseline", "Congestao", "Falha"]
    dj = [s1["dijkstra"]["penalized_latency"],
          s2["dijkstra"]["penalized_latency"],
          s3["dijkstra"]["penalized_latency"]]
    ql = [s1["qlearning"]["penalized_latency"],
          s2["qlearning"]["penalized_latency"],
          s3["qlearning"]["penalized_latency"]]

    x = range(len(cenarios))
    w = 0.35
    plt.figure(figsize=(8, 4.5))
    plt.bar([i - w / 2 for i in x], dj, w, color=COL_DIJKSTRA, label="Dijkstra")
    plt.bar([i + w / 2 for i in x], ql, w, color=COL_QLEARNING, label="Q-Learning")
    plt.xticks(list(x), cenarios)
    plt.ylabel("Latencia media penalizada (ms)")
    plt.title("Comparacao por cenario")
    plt.legend()
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    _save("comparacao_barras.png")


def escrever_csv(rows: list[dict]) -> None:
    path = os.path.join(RESULTS_DIR, "resultados.csv")
    cols = ["cenario", "roteador", "penalized_latency", "avg_latency",
            "worst_latency", "max_utilization", "congested_links",
            "dropped_flows", "delivered_flows"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nCSV salvo em {path}")


def _rows_from(cenario: str, snap: dict) -> list[dict]:
    out = []
    for rt in ("dijkstra", "qlearning"):
        m = dict(snap[rt])
        m["cenario"] = cenario
        m["roteador"] = rt
        out.append(m)
    return out


def _print_snap(snap: dict) -> None:
    for rt in ("dijkstra", "qlearning"):
        m = snap[rt]
        print(f"  {rt:10s} | lat_pen={m['penalized_latency']:7.2f} ms | "
              f"entregues={m['delivered_flows']} | descartados={m['dropped_flows']} | "
              f"util_max={m['max_utilization']:.2f}")


def _save(name: str) -> None:
    path = os.path.join(RESULTS_DIR, name)
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"  grafico salvo: {path}")


def main() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print("=" * 64)
    print(" Experimentos: Roteamento Dijkstra x Q-Learning")
    print("=" * 64)

    s1 = cenario1_baseline()
    s2 = cenario2_congestao()
    s3 = cenario3_falha()
    grafico_barras(s1, s2, s3)

    rows = (_rows_from("baseline", s1)
            + _rows_from("congestao", s2)
            + _rows_from("falha", s3))
    escrever_csv(rows)
    print("\nConcluido. Veja a pasta results/.")


if __name__ == "__main__":
    main()
