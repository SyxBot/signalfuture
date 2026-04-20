'use strict';

const TYPE = {
  AGGRESSIVE_LONGS: 'Aggressive Longs',
  AGGRESSIVE_SHORTS: 'Aggressive Shorts',
  SHORT_SQUEEZE: 'Short Squeeze',
  LONG_LIQUIDATION: 'Long Liquidation',
  UNKNOWN: 'Unknown'
};

/**
 * Classify a signal based on price direction and OI direction.
 *
 *  price↑ + OI↑  →  new longs entering (bullish conviction)
 *  price↓ + OI↑  →  new shorts entering (bearish conviction)
 *  price↑ + OI↓  →  shorts being squeezed / forced out
 *  price↓ + OI↓  →  longs being liquidated / exiting
 */
function classify(priceChangePct, oiDeltaPct) {
  const priceUp = priceChangePct > 0;
  const oiUp    = oiDeltaPct > 0;

  if (priceUp  && oiUp)  return TYPE.AGGRESSIVE_LONGS;
  if (!priceUp && oiUp)  return TYPE.AGGRESSIVE_SHORTS;
  if (priceUp  && !oiUp) return TYPE.SHORT_SQUEEZE;
  if (!priceUp && !oiUp) return TYPE.LONG_LIQUIDATION;

  return TYPE.UNKNOWN;
}

/**
 * Combine a spike event and OI data into a standardized signal object.
 * Score is set to 0 — caller must pass it through the scorer.
 *
 * @param {object} spike    output of SpikeDetector.process()
 * @param {object|null} oi  output of OpenInterestTracker.getDelta() — may be null
 * @returns {object}  standardized signal (score = 0)
 */
function buildSignal(spike, oi) {
  const oiDeltaUsd = oi?.oiDeltaUsd ?? 0;
  const oiDeltaPct = oi?.oiDeltaPct ?? 0;

  return {
    symbol: spike.symbol,
    timestamp: spike.timestamp,
    price: spike.price,
    volumeMultiple: spike.volumeMultiple,
    priceChangePct: spike.priceChangePct,
    oiDeltaUsd: Math.round(oiDeltaUsd),
    oiDeltaPct: Math.round(oiDeltaPct * 100) / 100,
    type: classify(spike.priceChangePct, oiDeltaPct),
    score: 0
  };
}

module.exports = { buildSignal, classify, TYPE };
