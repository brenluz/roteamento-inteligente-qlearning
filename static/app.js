// Dashboard: consulta /api/state por polling, desenha a topologia com
// vis-network (enlaces coloridos pela utilizacao), destaca a rota do fluxo
// selecionado e plota a latencia comparativa com Chart.js.

let mode = "qlearning";        // roteador cuja carga e visualizada
let selectedEdge = null;        // {u, v} do enlace selecionado no grafo
let network = null;
let nodesDS = null, edgesDS = null;
let chart = null;
let flowsLoaded = false;
let edgesLoaded = false;

const METRIC_LABELS = {
  penalized_latency: "Latência penalizada (ms)",
  avg_latency: "Latência média entregue (ms)",
  worst_latency: "Pior latência (ms)",
  max_utilization: "Utilização máxima",
  congested_links: "Enlaces congestionados",
  dropped_flows: "Fluxos descartados",
  delivered_flows: "Fluxos entregues",
};
// Para estas metricas, MENOR e melhor (define quem "vence" em negrito).
const LOWER_BETTER = new Set([
  "penalized_latency", "worst_latency", "max_utilization",
  "congested_links", "dropped_flows",
]);

// ---------------------------------------------------------------- cores de carga
function utilColor(u) {
  if (u >= 0.90) return "#e74c3c";  // congestionado
  if (u >= 0.75) return "#e67e22";  // alto
  if (u >= 0.50) return "#f1c40f";  // moderado
  return "#2ecc71";                 // livre
}

function pathEdgeSet(path) {
  const s = new Set();
  for (let i = 0; i < path.length - 1; i++) {
    s.add(edgeKey(path[i], path[i + 1]));
  }
  return s;
}
function edgeKey(a, b) { return a < b ? `${a}|${b}` : `${b}|${a}`; }

// ------------------------------------------------------------------- inicializacao
function initNetwork(state) {
  const nodes = state.nodes.map(n => ({
    id: n.id, label: n.id,
    x: n.x * 150, y: (2 - n.y) * 140, fixed: true,
    shape: "circle", size: 18,
    color: { background: "#3a4a5e", border: "#5b6b7e" },
    font: { color: "#ffffff", size: 18, face: "Segoe UI" },
  }));
  const edges = state.edges.map(e => ({
    id: edgeKey(e.source, e.target),
    from: e.source, to: e.target, width: 2,
  }));
  nodesDS = new vis.DataSet(nodes);
  edgesDS = new vis.DataSet(edges);

  network = new vis.Network(
    document.getElementById("net"),
    { nodes: nodesDS, edges: edgesDS },
    {
      physics: false,
      interaction: {
        hover: true, dragNodes: false, zoomView: true,
        selectConnectedEdges: false, hoverConnectedEdges: false,
      },
      edges: { smooth: false, color: { inherit: false }, selectionWidth: 4 },
    }
  );

  // Garante que toda a topologia caiba na area visivel.
  setTimeout(() => network && network.fit({ animation: false }), 80);
  window.addEventListener("resize", () => network && network.fit({ animation: false }));

  network.on("selectEdge", (params) => {
    if (params.edges.length) {
      const [u, v] = params.edges[0].split("|");
      setSelectedEdge(u, v, false);
    }
  });
  network.on("deselectEdge", () => clearSelectedEdge());
}

// Define o enlace selecionado a partir do clique no grafo ou do dropdown.
function setSelectedEdge(u, v, fromDropdown) {
  selectedEdge = { u, v };
  document.getElementById("sel").textContent = `${u} – ${v}`;
  const sel = document.getElementById("edge");
  if (sel) sel.value = edgeKey(u, v);
  if (fromDropdown && network) {
    try { network.selectEdges([edgeKey(u, v)]); } catch (e) { /* ignore */ }
  }
}

function clearSelectedEdge() {
  selectedEdge = null;
  document.getElementById("sel").textContent = "—";
  const sel = document.getElementById("edge");
  if (sel) sel.value = "";
}

// ------------------------------------------------------------------- atualizacao
function updateGraph(state) {
  const utilKey = mode === "dijkstra" ? "util_dijkstra" : "util_qlearning";
  const path = state.paths[mode] || [];
  const onPath = pathEdgeSet(path);
  const haloColor = mode === "dijkstra" ? "#0275d8" : "#f39c12";

  const updates = state.edges.map(e => {
    const key = edgeKey(e.source, e.target);
    const u = e[utilKey] || 0;
    if (!e.up) {
      return {
        id: key, width: 2, dashes: [4, 6],
        color: { color: "#556", highlight: "#889", hover: "#889" },
        shadow: { enabled: false }, label: undefined,
      };
    }
    const isPath = onPath.has(key);
    return {
      id: key,
      width: isPath ? 6 : 2,
      dashes: false,
      color: { color: utilColor(u), highlight: utilColor(u), hover: utilColor(u) },
      shadow: isPath
        ? { enabled: true, color: haloColor, size: 16, x: 0, y: 0 }
        : { enabled: false },
      label: e.injected ? "⚠" : undefined,
      font: { color: "#e74c3c", size: 20 },
    };
  });
  edgesDS.update(updates);
  document.getElementById("step").textContent = state.step;
}

function updateMetrics(state) {
  const dj = state.metrics.dijkstra;
  const ql = state.metrics.qlearning;
  const tbody = document.querySelector("#metrics tbody");
  tbody.innerHTML = "";
  for (const key of Object.keys(METRIC_LABELS)) {
    const tr = document.createElement("tr");
    const dv = dj[key], qv = ql[key];
    let winner = "";
    if (dv !== qv) {
      const qlWins = LOWER_BETTER.has(key) ? qv < dv : qv > dv;
      winner = qlWins ? "win-ql" : "win-dj";
    }
    tr.className = winner;
    tr.innerHTML =
      `<td>${METRIC_LABELS[key]}</td>` +
      `<td class="v-dj">${dv}</td>` +
      `<td class="v-ql">${qv}</td>`;
    tbody.appendChild(tr);
  }
}

function updateChart(state) {
  const labels = state.history.map(h => h.step);
  const dj = state.history.map(h => h.dijkstra);
  const ql = state.history.map(h => h.qlearning);
  if (!chart) {
    chart = new Chart(document.getElementById("chart"), {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Dijkstra", data: dj, borderColor: "#d9534f",
            backgroundColor: "transparent", tension: 0.2, pointRadius: 0 },
          { label: "Q-Learning", data: ql, borderColor: "#0275d8",
            backgroundColor: "transparent", tension: 0.2, pointRadius: 0 },
        ],
      },
      options: {
        animation: false, responsive: true,
        scales: {
          x: { ticks: { color: "#8b98a5" }, grid: { color: "#2d3742" } },
          y: { ticks: { color: "#8b98a5" }, grid: { color: "#2d3742" },
               title: { display: true, text: "ms", color: "#8b98a5" } },
        },
        plugins: { legend: { labels: { color: "#e6edf3" } } },
      },
    });
  } else {
    chart.data.labels = labels;
    chart.data.datasets[0].data = dj;
    chart.data.datasets[1].data = ql;
    chart.update();
  }
}

function loadFlows(state) {
  if (flowsLoaded) return;
  const sel = document.getElementById("flow");
  state.flows.forEach(f => {
    const o = document.createElement("option");
    o.value = f; o.textContent = f;
    if (f === state.highlight) o.selected = true;
    sel.appendChild(o);
  });
  flowsLoaded = true;
}

function loadEdges(state) {
  if (edgesLoaded) return;
  const sel = document.getElementById("edge");
  const ph = document.createElement("option");
  ph.value = ""; ph.textContent = "— escolha —";
  sel.appendChild(ph);
  // Ordena os enlaces alfabeticamente para facilitar achar na lista.
  const keys = state.edges
    .map(e => edgeKey(e.source, e.target))
    .sort();
  keys.forEach(k => {
    const [u, v] = k.split("|");
    const o = document.createElement("option");
    o.value = k; o.textContent = `${u} – ${v}`;
    sel.appendChild(o);
  });
  edgesLoaded = true;
}

// --------------------------------------------------------------------- polling
async function poll() {
  try {
    const r = await fetch("/api/state");
    const state = await r.json();
    if (!network) initNetwork(state);
    loadFlows(state);
    loadEdges(state);
    updateGraph(state);
    updateMetrics(state);
    updateChart(state);
  } catch (e) { /* servidor reiniciando; ignora */ }
}

// ----------------------------------------------------------------------- eventos
async function sendEvent(body) {
  await fetch("/api/event", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  poll();
}

function requireEdge() {
  if (!selectedEdge) { alert("Selecione um enlace no grafo primeiro."); return null; }
  return selectedEdge;
}

document.querySelectorAll(".mode-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    mode = btn.dataset.mode;
    poll();
  });
});

document.getElementById("edge").addEventListener("change", (e) => {
  if (!e.target.value) { clearSelectedEdge(); return; }
  const [u, v] = e.target.value.split("|");
  setSelectedEdge(u, v, true);
});

document.getElementById("flow").addEventListener("change", async (e) => {
  await fetch("/api/highlight", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ flow: e.target.value }),
  });
  poll();
});

document.getElementById("btn-congest").onclick = () => {
  const s = requireEdge(); if (s) sendEvent({ type: "congest", u: s.u, v: s.v });
};
document.getElementById("btn-drop").onclick = () => {
  const s = requireEdge(); if (s) sendEvent({ type: "drop", u: s.u, v: s.v });
};
document.getElementById("btn-restore").onclick = () => {
  const s = requireEdge(); if (s) sendEvent({ type: "restore", u: s.u, v: s.v });
};
document.getElementById("btn-restore-all").onclick = () => sendEvent({ type: "restore_all" });
document.getElementById("btn-reset").onclick = () => {
  flowsLoaded = false; edgesLoaded = false;
  document.getElementById("flow").innerHTML = "";
  document.getElementById("edge").innerHTML = "";
  clearSelectedEdge();
  sendEvent({ type: "reset" });
};

document.querySelectorAll("[data-demo]").forEach(btn => {
  btn.addEventListener("click", async () => {
    if (btn.dataset.demo === "congest-bc") {
      await sendEvent({ type: "congest", u: "B", v: "C" });
    } else if (btn.dataset.demo === "fail-cd") {
      await sendEvent({ type: "drop", u: "C", v: "D" });
      await sendEvent({ type: "congest", u: "G", v: "H" });
    }
  });
});

poll();
setInterval(poll, 700);
