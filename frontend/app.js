const els = {
  start: document.getElementById("startBtn"),
  stop: document.getElementById("stopBtn"),
  status: document.getElementById("statusText"),
  accountsInput: document.getElementById("accountsInput"),
  txnsInput: document.getElementById("txnsInput"),
  speedInput: document.getElementById("speedInput"),
  accounts: document.getElementById("accounts"),
  transactions: document.getElementById("transactions"),
  tps: document.getElementById("tps"),
  fraud: document.getElementById("fraud"),
  mules: document.getElementById("mules"),
  rejected: document.getElementById("rejected"),
  neoNodes: document.getElementById("neoNodes"),
  neoEdges: document.getElementById("neoEdges"),
  pid: document.getElementById("pid"),
  database: document.getElementById("database"),
  graph: document.getElementById("graphCanvas"),
};

const fmt = new Intl.NumberFormat("en-IN");

function setBusy(isBusy) {
  els.start.disabled = false;
  els.stop.disabled = true;
}

async function post(path) {
  const response = await fetch(path, { method: "POST" });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

async function startSimulation() {
  els.status.textContent = "Attaching...";
  try {
    await post("/api/start");
    await refreshMetrics();
  } catch (err) {
    els.status.textContent = err.message;
  }
}

async function stopSimulation() {
  els.status.textContent = "Runner is managed in the terminal.";
  try {
    await post("/api/stop");
    await refreshMetrics();
  } catch (err) {
    els.status.textContent = err.message;
  }
}

async function refreshMetrics() {
  const response = await fetch("/api/metrics", { cache: "no-store" });
  const data = await response.json();
  els.status.textContent = `Status: ${data.status}`;
  els.accounts.textContent = fmt.format(data.total_accounts);
  els.transactions.textContent = fmt.format(data.total_transactions);
  els.tps.textContent = fmt.format(data.transactions_per_second);
  els.fraud.textContent = fmt.format(data.fraud_events);
  els.mules.textContent = fmt.format(data.mule_accounts);
  els.rejected.textContent = fmt.format(data.rejected_transactions);
  els.neoNodes.textContent = fmt.format(data.neo4j_nodes);
  els.neoEdges.textContent = fmt.format(data.neo4j_edges);
  els.pid.textContent = data.pid || "external ./guard.sh";
  els.database.textContent = data.database;
  setBusy(data.status === "running");
  drawGraph(data);
}

els.start.addEventListener("click", startSimulation);
els.stop.addEventListener("click", stopSimulation);

refreshMetrics();
setInterval(refreshMetrics, 1000);

function drawGraph(data) {
  const canvas = els.graph;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  const nodes = Math.min(90, Math.max(12, Math.floor((data.total_accounts || 0) / 1200)));
  const edges = Math.min(180, Math.max(12, Math.floor((data.total_transactions || 0) / 3000)));
  const points = [];
  for (let i = 0; i < nodes; i += 1) {
    const angle = (i / nodes) * Math.PI * 2;
    const ring = i % 3;
    points.push({
      x: w / 2 + Math.cos(angle) * (110 + ring * 60),
      y: h / 2 + Math.sin(angle) * (45 + ring * 22),
    });
  }
  ctx.strokeStyle = "#c6d3dc";
  ctx.lineWidth = 1;
  for (let i = 0; i < edges; i += 1) {
    const a = points[i % points.length];
    const b = points[(i * 17 + 7) % points.length];
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.fillStyle = "#0f766e";
  for (const p of points) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }
}
