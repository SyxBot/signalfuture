'use strict';

/**
 * Detects abnormal volume spikes on closed 1-minute candles.
 *
 * Strategy: if current candle volume >= threshold * rolling_avg(last N candles),
 * a spike is emitted. Per-symbol cooldown prevents signal flooding.
 */
class SpikeDetector {
  /**
   * @param {object} opts
   * @param {number} opts.threshold     volume multiple required to trigger (default 3.0)
   * @param {number} opts.windowSize    rolling average window in candles (default 20)
   * @param {number} opts.cooldownMs    min ms between signals per symbol (default 120000)
   */
  constructor(opts = {}) {
    this.threshold = opts.threshold ?? 3.0;
    this.windowSize = opts.windowSize ?? 20;
    this.cooldownMs = opts.cooldownMs ?? 120_000;

    // Map<symbol, Array<{volume, quoteVolume, close, open, high, low, t}>>
    this._candles = new Map();
    // Map<symbol, lastAlertTimestamp>
    this._lastAlert = new Map();
  }

  /**
   * Feed a raw Binance kline event (from the combined stream).
   *
   * @param {object} klineEvent  the `data` field from the combined stream message
   * @returns {{ symbol, timestamp, price, volume, quoteVolume, avgVolume,
   *             volumeMultiple, priceChangePct, candleTs } | null}
   */
  process(klineEvent) {
    const k = klineEvent.k;

    // Only act on closed candles
    if (!k.x) return null;

    const symbol = klineEvent.s;
    const volume = parseFloat(k.v);       // base asset volume
    const quoteVolume = parseFloat(k.q);  // quote (USD) volume
    const close = parseFloat(k.c);
    const open = parseFloat(k.o);

    if (!this._candles.has(symbol)) this._candles.set(symbol, []);
    const history = this._candles.get(symbol);

    // Need a full window before we can compute a meaningful average
    if (history.length < this.windowSize) {
      history.push({ volume, quoteVolume, close });
      return null;
    }

    // Average over the previous N candles (not including this one)
    const window = history.slice(-this.windowSize);
    const avgVolume = window.reduce((s, c) => s + c.volume, 0) / this.windowSize;
    const volumeMultiple = avgVolume > 0 ? volume / avgVolume : 0;

    // Slide the window
    history.push({ volume, quoteVolume, close });
    if (history.length > this.windowSize + 5) history.shift();

    if (volumeMultiple < this.threshold) return null;

    // Per-symbol cooldown
    const now = Date.now();
    if (now - (this._lastAlert.get(symbol) || 0) < this.cooldownMs) return null;
    this._lastAlert.set(symbol, now);

    const priceChangePct = open > 0 ? ((close - open) / open) * 100 : 0;

    return {
      symbol,
      timestamp: now,
      price: close,
      volume,
      quoteVolume,
      avgVolume,
      volumeMultiple: Math.round(volumeMultiple * 10) / 10,
      priceChangePct: Math.round(priceChangePct * 100) / 100,
      candleTs: k.t
    };
  }
}

module.exports = { SpikeDetector };
