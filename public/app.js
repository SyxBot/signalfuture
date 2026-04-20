/* ZookAgent Frontend — SSE-driven real-time signal dashboard */
(function () {
  'use strict';

  // ── DOM refs ────────────────────────────────────────────────────────────────
  const tbody      = document.getElementById('signal-tbody');
  const emptyRow   = document.getElementById('empty-row');
  const statCount  = document.getElementById('stat-count');
  const statSymbols = document.getElementById('stat-symbols');
  const connDot    = document.getElementById('conn-dot');
  const connLabel  = document.getElementById('conn-label');
  const filterType = document.getElementById('filter-type');
  const filterScore = document.getElementById('filter-score');
  const filterSymbol = document.getElementById('filter-symbol');
  const btnReset   = document.getElementById('btn-reset');

  // ── State ───────────────────────────────────────────────────────────────────
  const MAX_SIGNALS = 500;
  let signals   = [];        // full signal list, newest-first
  let sse       = null;
  let pollTimer = null;
  let symbolCount = 0;

  // ── Signal type config ──────────────────────────────────────────────────────
  const TYPE_CLASS = {
    'Aggressive Longs':  'type-long',
    'Aggressive Shorts': 'type-short',
    'Short Squeeze':     'type-squeeze',
    'Long Liquidation':  'type-liq'
  };

  // ── Formatters ──────────────────────────────────────────────────────────────
  function fmtTime(ts) {
    const d = new Date(ts);
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
  }

  function fmtPrice(p) {
    if (p >= 10000) return '$' + p.toLocaleString('en-US', { maximumFractionDigits: 0 });
    if (p >= 1)     return '$' + p.toFixed(2);
    return '$' + p.toPrecision(4);
  }

  function fmtPct(v) {
    const s = (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
    return s;
  }

  function fmtUsd(v) {
    const abs = Math.abs(v);
    const prefix = v >= 0 ? '+$' : '-$';
    if (abs >= 1e9) return prefix + (abs / 1e9).toFixed(2) + 'B';
    if (abs >= 1e6) return prefix + (abs / 1e6).toFixed(2) + 'M';
    if (abs >= 1e3) return prefix + (abs / 1e3).toFixed(1) + 'K';
    return prefix + abs.toFixed(0);
  }

  function scoreClass(s) {
    if (s >= 8) return 'score-hot';
    if (s >= 5) return 'score-high';
    if (s >= 3) return 'score-mid';
    return 'score-low';
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ── Row builder ─────────────────────────────────────────────────────────────
  function buildRow(sig, isNew) {
    const tc  = TYPE_CLASS[sig.type] || 'type-other';
    const pDir = sig.priceChangePct >= 0 ? 'positive' : 'negative';
    const oDir = sig.oiDeltaUsd      >= 0 ? 'positive' : 'negative';

    return `<tr class="${isNew ? 'new-row' : ''}">
      <td class="cell-time">${fmtTime(sig.timestamp)}</td>
      <td class="cell-symbol">${esc(sig.symbol)}</td>
      <td><span class="type-badge ${tc}">${esc(sig.type)}</span></td>
      <td class="cell-score col-r"><span class="${scoreClass(sig.score)}">${sig.score.toFixed(1)}</span></td>
      <td class="cell-vol col-r positive">${sig.volumeMultiple.toFixed(1)}×</td>
      <td class="cell-price-pct col-r ${pDir}">${fmtPct(sig.priceChangePct)}</td>
      <td class="cell-oi col-r ${oDir}">${fmtUsd(sig.oiDeltaUsd)}</td>
      <td class="cell-price col-r">${fmtPrice(sig.price)}</td>
    </tr>`;
  }

  // ── Filtering & rendering ───────────────────────────────────────────────────
  function getFiltered() {
    const type     = filterType.value;
    const minScore = parseFloat(filterScore.value) || 0;
    const sym      = filterSymbol.value.trim().toUpperCase();

    return signals.filter(s => {
      if (type && s.type !== type)             return false;
      if (s.score < minScore)                  return false;
      if (sym && !s.symbol.includes(sym))      return false;
      return true;
    });
  }

  function render() {
    const filtered = getFiltered();
    statCount.textContent = filtered.length;

    if (filtered.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="empty-cell">No signals match your filters.</td></tr>';
      return;
    }

    tbody.innerHTML = filtered.slice(0, 100).map((s, i) => buildRow(s, false)).join('');
  }

  // ── Add a single new signal (SSE path) ─────────────────────────────────────
  function addSignal(sig) {
    // Deduplicate by symbol+timestamp
    if (signals.some(s => s.symbol === sig.symbol && s.timestamp === sig.timestamp)) return;

    signals.unshift(sig);
    if (signals.length > MAX_SIGNALS) signals.pop();

    // Track distinct symbol count
    const seen = new Set(signals.map(s => s.symbol));
    symbolCount = seen.size;
    statSymbols.textContent = seen.size;

    render();
  }

  // ── Load initial signals (REST bootstrap + polling fallback) ────────────────
  async function fetchLatest() {
    try {
      const res = await fetch('/signals?limit=50');
      if (!res.ok) return;
      const data = await res.json();
      // Bootstrap: add oldest-first so newest ends up at top
      for (const s of [...data].reverse()) addSignal(s);
    } catch (_) {}
  }

  // ── SSE connection ──────────────────────────────────────────────────────────
  function setConn(state) {
    connDot.className = 'conn-dot ' + state;
    const labels = { live: 'Live', polling: 'Polling', dead: 'Disconnected', '': 'Connecting' };
    connLabel.textContent = labels[state] || 'Connecting';
  }

  function connectSSE() {
    if (sse) { sse.close(); sse = null; }

    sse = new EventSource('/stream');

    sse.onopen = () => {
      setConn('live');
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    };

    sse.onmessage = (e) => {
      try { addSignal(JSON.parse(e.data)); } catch (_) {}
    };

    sse.onerror = () => {
      setConn('dead');
      sse.close();
      sse = null;
      // Fall back to polling, retry SSE after 10s
      startPolling();
      setTimeout(connectSSE, 10_000);
    };
  }

  function startPolling() {
    if (pollTimer) return;
    setConn('polling');
    pollTimer = setInterval(fetchLatest, 5_000);
  }

  // ── Filter controls ─────────────────────────────────────────────────────────
  filterType.addEventListener('change', render);
  filterScore.addEventListener('input', render);
  filterSymbol.addEventListener('input', render);

  btnReset.addEventListener('click', () => {
    filterType.value   = '';
    filterScore.value  = '0';
    filterSymbol.value = '';
    render();
  });

  // ── Init ────────────────────────────────────────────────────────────────────
  // Load existing data from REST, then open SSE for live updates
  fetchLatest().then(() => connectSSE());

  // Fetch symbol count from health endpoint
  fetch('/health')
    .then(r => r.json())
    .catch(() => null);

})();
