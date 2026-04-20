'use strict';

/**
 * Score a signal based on three weighted factors:
 *
 *   score = (volumeMultiple * 0.4) + (|priceChangePct| * 0.3) + (|oiDeltaPct| * 0.3)
 *
 * Weights reflect that volume is the primary trigger; price move and OI shift
 * provide corroborating context.
 */
function score(signal) {
  const s =
    (signal.volumeMultiple        * 0.4) +
    (Math.abs(signal.priceChangePct) * 0.3) +
    (Math.abs(signal.oiDeltaPct)     * 0.3);

  return Math.round(s * 10) / 10;
}

/**
 * Return the signal with its computed score attached.
 * @param {object} signal
 * @returns {object}
 */
function scoreSignal(signal) {
  return { ...signal, score: score(signal) };
}

/**
 * @param {object} signal
 * @param {number} threshold  default 2.0
 */
function isAboveThreshold(signal, threshold = 2.0) {
  return signal.score >= threshold;
}

module.exports = { score, scoreSignal, isAboveThreshold };
