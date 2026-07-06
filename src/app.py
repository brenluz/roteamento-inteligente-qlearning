"""Servidor Flask do dashboard de roteamento inteligente.

Uma thread de fundo avanca a simulacao continuamente (o agente Q-Learning
treina a cada passo). O front-end (static/) consulta /api/state por polling e
envia eventos (congestionar/derrubar/restaurar/reset) por /api/event, alem de
escolher qual fluxo destacar e qual roteador visualizar.

Execucao:
    python src/app.py
    -> abra http://localhost:5000
"""

from __future__ import annotations

import os
import threading
import time

from flask import Flask, jsonify, request, send_from_directory

# Suporta execucao tanto como modulo (`python -m src.app`) quanto script
# direto (`python src/app.py`).
try:
    from .simulator import Simulator
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.simulator import Simulator

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

app = Flask(__name__, static_folder=None)
sim = Simulator(warmup_episodes=5000)

# Passo automatico da simulacao em thread de fundo.
STEP_INTERVAL = 0.6  # segundos entre passos
_running = True


def _sim_loop() -> None:
    while _running:
        sim.step()
        time.sleep(STEP_INTERVAL)


# ---------------------------------------------------------------- paginas estaticas
@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(STATIC_DIR, path)


# --------------------------------------------------------------------------- API
@app.route("/api/state")
def api_state():
    return jsonify(sim.state())


@app.route("/api/event", methods=["POST"])
def api_event():
    data = request.get_json(force=True) or {}
    kind = data.get("type")
    u, v = data.get("u"), data.get("v")

    if kind == "congest" and u and v:
        ok = sim.congest(u, v)
    elif kind == "drop" and u and v:
        ok = sim.drop_link(u, v)
    elif kind == "restore" and u and v:
        ok = sim.restore_link(u, v)
    elif kind == "restore_all":
        sim.restore_all()
        ok = True
    elif kind == "reset":
        sim.reset()
        ok = True
    else:
        return jsonify({"ok": False, "error": "evento invalido"}), 400
    return jsonify({"ok": ok})


@app.route("/api/highlight", methods=["POST"])
def api_highlight():
    data = request.get_json(force=True) or {}
    fid = data.get("flow")
    if fid:
        sim.set_highlight(fid)
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 400


def main() -> None:
    t = threading.Thread(target=_sim_loop, daemon=True)
    t.start()
    # use_reloader=False para nao iniciar a simulacao duas vezes.
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
