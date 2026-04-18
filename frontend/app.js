const API = "http://localhost:8000";

// ── State ──────────────────────────────────────────────────────────────────
let allTokens = [];
let es = null;

// ── SSE ────────────────────────────────────────────────────────────────────
function connectSSE() {
  setStatus("connecting");
  es = new EventSource(`${API}/api/stream`);

  es.onopen = () => setStatus("connected");

  es.onmessage = (e) => {
    try {
      const tokens = JSON.parse(e.data);
      mergeTokens(tokens);
      renderTokens(allTokens);
    } catch (err) {
      console.warn("SSE parse error:", err);
    }
  };

  es.onerror = () => {
    setStatus("disconnected");
    es.close();
    setTimeout(connectSSE, 5000);
  };
}

function mergeTokens(incoming) {
  const map = new Map(allTokens.map(t => [t.mint, t]));
  incoming.forEach(t => map.set(t.mint, t));
  allTokens = [...map.values()].sort((a, b) => (b.smart_buy_24h - a.smart_buy_24h) || (b.volume_24h_usd - a.volume_24h_usd));
}

// ── Filters ────────────────────────────────────────────────────────────────
function readFilters() {
  const v = (id) => document.getElementById(id).value;
  const c = (id) => document.getElementById(id).checked;
  const num = (id, fallback) => { const n = parseFloat(v(id)); return isNaN(n) ? fallback : n; };

  return {
    min_liquidity_usd:    num("f-liquidity", 0),
    min_real_volume_usd:  num("f-volume", 0),
    min_market_cap_usd:   num("f-mc-min", 0),
    max_market_cap_usd:   num("f-mc-max", Infinity),
    max_age_seconds:      num("f-age", 720) * 3600,
    min_holder_count:     num("f-holders", 0),
    max_top10_holder_pct: num("f-top10", 100),
    min_buy_sell_ratio:   num("f-bsr", 0),
    max_buy_tax:          num("f-buy-tax", 100),
    max_sell_tax:         num("f-sell-tax", 100),
    min_smart_buy_24h:    num("f-sm-buy", 0),
    require_renounced:    c("f-renounced"),
    require_lp_burned:    c("f-lp-burned"),
    exclude_honeypots:    c("f-no-honeypot"),
  };
}

async function applyFilters() {
  const criteria = readFilters();
  try {
    const resp = await fetch(`${API}/api/filters/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(criteria),
    });
    if (!resp.ok) throw new Error(resp.statusText);
    const tokens = await resp.json();
    renderTokens(tokens);
  } catch (err) {
    console.error("Filter apply failed:", err);
  }
}

function resetFilters() {
  document.getElementById("f-liquidity").value = 0;
  document.getElementById("f-volume").value = 0;
  document.getElementById("f-mc-min").value = 0;
  document.getElementById("f-mc-max").value = "";
  document.getElementById("f-age").value = 720;
  document.getElementById("f-holders").value = 0;
  document.getElementById("f-top10").value = 100;
  document.getElementById("f-bsr").value = 0;
  document.getElementById("f-buy-tax").value = 10;
  document.getElementById("f-sell-tax").value = 10;
  document.getElementById("f-sm-buy").value = 0;
  document.getElementById("f-renounced").checked = false;
  document.getElementById("f-lp-burned").checked = false;
  document.getElementById("f-no-honeypot").checked = true;
  renderTokens(allTokens);
}

// ── Render ─────────────────────────────────────────────────────────────────
function renderTokens(tokens) {
  const grid = document.getElementById("token-grid");
  const empty = document.getElementById("empty-msg");
  const count = document.getElementById("token-count");

  count.textContent = `${tokens.length} token${tokens.length !== 1 ? "s" : ""}`;

  if (tokens.length === 0) {
    grid.innerHTML = "";
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  grid.innerHTML = "";
  tokens.forEach(t => grid.appendChild(buildCard(t)));
}

function buildCard(t) {
  const el = document.createElement("div");
  el.className = "token-card";

  const ageStr = formatAge(t.age_seconds);
  const logoSrc = t.logo_uri || "";

  el.innerHTML = `
    <div class="card-header">
      ${logoSrc ? `<img src="${escHtml(logoSrc)}" alt="" loading="lazy" onerror="this.style.display='none'" />` : '<div style="width:34px;height:34px;border-radius:50%;background:var(--border);flex-shrink:0"></div>'}
      <div class="name-block">
        <div class="symbol">${escHtml(t.symbol)}</div>
        <div class="name">${escHtml(t.name || t.symbol)}</div>
      </div>
      <div class="card-price">$${fmtPrice(t.price_usd)}</div>
    </div>

    <div class="card-stats">
      <div class="stat"><span class="label">Market Cap</span><span class="value">$${fmtNum(t.market_cap_usd)}</span></div>
      <div class="stat"><span class="label">Liquidity</span><span class="value">$${fmtNum(t.liquidity_usd)}</span></div>
      <div class="stat"><span class="label">Vol 24h (real)</span><span class="value">$${fmtNum(t.real_volume_24h_usd)}</span></div>
      <div class="stat"><span class="label">Vol 1h</span><span class="value">$${fmtNum(t.volume_1h_usd)}</span></div>
      <div class="stat"><span class="label">Holders</span><span class="value">${fmtNum(t.holder_count, true)}</span></div>
      <div class="stat"><span class="label">Top-10 %</span><span class="value">${t.top10_holder_pct.toFixed(1)}%</span></div>
      <div class="stat"><span class="label">B/S Ratio</span><span class="value">${t.buy_sell_ratio.toFixed(2)}</span></div>
      <div class="stat"><span class="label">Smart Buys 24h</span><span class="value">${t.smart_buy_24h}</span></div>
    </div>

    <div class="card-flags">
      ${t.contract_renounced ? '<span class="badge renounced">✔ Renounced</span>' : ""}
      ${t.lp_burned          ? '<span class="badge lp-burned">🔥 LP Burned</span>' : ""}
      ${t.is_honeypot        ? '<span class="badge honeypot">⚠ Honeypot</span>'   : ""}
      ${t.smart_money_count > 0 ? `<span class="badge sm">SM: ${t.smart_money_count}</span>` : ""}
      <span class="badge source">${escHtml(t.source)}</span>
    </div>

    <div class="card-age">Age: ${ageStr}</div>
  `;
  return el;
}

// ── Helpers ────────────────────────────────────────────────────────────────
function fmtNum(n, integer = false) {
  if (n === null || n === undefined || n === 0) return "—";
  if (n >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return integer ? Math.round(n).toString() : n.toFixed(0);
}

function fmtPrice(p) {
  if (!p) return "0";
  if (p < 0.000001) return p.toExponential(2);
  if (p < 0.01)     return p.toFixed(6);
  if (p < 1)        return p.toFixed(4);
  return p.toFixed(2);
}

function formatAge(secs) {
  if (!secs) return "—";
  if (secs < 60)     return `${secs}s`;
  if (secs < 3600)   return `${Math.floor(secs / 60)}m`;
  if (secs < 86400)  return `${Math.floor(secs / 3600)}h`;
  return `${Math.floor(secs / 86400)}d`;
}

function setStatus(state) {
  const dot = document.getElementById("status-dot");
  dot.className = `dot ${state}`;
  dot.title = state;
}

function escHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Bootstrap ──────────────────────────────────────────────────────────────
document.getElementById("apply-btn").addEventListener("click", applyFilters);
document.getElementById("reset-btn").addEventListener("click", resetFilters);

connectSSE();
