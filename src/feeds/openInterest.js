'use strict';

const FAPI_BASE = 'https://fapi.binance.com/fapi/v1';
const POLL_INTERVAL_MS = 30_000;
const REQUEST_GAP_MS = 150; // gentle pacing to stay under rate limits

class OpenInterestTracker {
  constructor(symbols) {
    this.symbols = symbols;
    // Map<symbol, { contracts: number, timestamp: number }>
    this._current = new Map();
    this._previous = new Map();
    this._timer = null;
  }

  async start() {
    await this._pollAll();
    this._timer = setInterval(() => this._pollAll(), POLL_INTERVAL_MS);
  }

  stop() {
    if (this._timer) clearInterval(this._timer);
  }

  /**
   * Returns OI change data for a symbol given the current asset price.
   * oiDeltaUsd = (contracts_now - contracts_prev) * price
   *
   * @param {string} symbol
   * @param {number} currentPrice  price of the base asset in USD
   * @returns {{ oi: number, oiDelta: number, oiDeltaPct: number, oiDeltaUsd: number } | null}
   */
  getDelta(symbol, currentPrice) {
    const curr = this._current.get(symbol);
    if (curr === undefined) return null;

    const prev = this._previous.has(symbol) ? this._previous.get(symbol) : curr;
    const oiDelta = curr - prev;
    const oiDeltaPct = prev > 0 ? (oiDelta / prev) * 100 : 0;
    const oiDeltaUsd = oiDelta * (currentPrice || 0);

    return { oi: curr, oiDelta, oiDeltaPct, oiDeltaUsd };
  }

  async _pollAll() {
    for (const symbol of this.symbols) {
      await this._fetchOI(symbol);
      await _sleep(REQUEST_GAP_MS);
    }
  }

  async _fetchOI(symbol) {
    try {
      const res = await fetch(`${FAPI_BASE}/openInterest?symbol=${symbol}`);
      if (!res.ok) return;
      const data = await res.json();
      const contracts = parseFloat(data.openInterest);
      if (isNaN(contracts)) return;

      // Rotate: current → previous, fresh value → current
      if (this._current.has(symbol)) {
        this._previous.set(symbol, this._current.get(symbol));
      }
      this._current.set(symbol, contracts);
    } catch (_) {
      // Silently skip — OI data is supplementary, not critical
    }
  }
}

function _sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

module.exports = { OpenInterestTracker };
