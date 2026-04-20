'use strict';

const TELEGRAM_API = 'https://api.telegram.org';

/**
 * Sends a Telegram alert for signals that exceed TELEGRAM_MIN_SCORE.
 * Silently no-ops if TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID are unset.
 *
 * @param {object} signal  scored signal object
 */
async function sendAlert(signal) {
  const token   = process.env.TELEGRAM_BOT_TOKEN;
  const chatId  = process.env.TELEGRAM_CHAT_ID;
  const minScore = parseFloat(process.env.TELEGRAM_MIN_SCORE ?? '5.0');

  if (!token || !chatId) return;
  if (signal.score < minScore) return;

  const oiStr    = _formatUsd(signal.oiDeltaUsd, true);
  const priceStr = _formatPct(signal.priceChangePct);
  const typeEmoji = _typeEmoji(signal.type);

  const text = [
    `${typeEmoji} *${signal.symbol}*`,
    `Type: ${signal.type}`,
    `OI Δ: ${oiStr}`,
    `Price Δ: ${priceStr}`,
    `Vol: ${signal.volumeMultiple.toFixed(1)}× avg`,
    `Score: *${signal.score}*`
  ].join('\n');

  try {
    const url = `${TELEGRAM_API}/bot${token}/sendMessage`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'Markdown' }),
      signal: AbortSignal.timeout(5000)
    });
    if (!res.ok) {
      const body = await res.text();
      console.error('[Telegram] API error:', res.status, body);
    }
  } catch (err) {
    console.error('[Telegram] Send failed:', err.message);
  }
}

function _formatUsd(value, signed = false) {
  const abs = Math.abs(value);
  const prefix = signed ? (value >= 0 ? '+' : '-') : '';
  if (abs >= 1e9) return `${prefix}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${prefix}$${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${prefix}$${(abs / 1e3).toFixed(1)}K`;
  return `${prefix}$${abs.toFixed(0)}`;
}

function _formatPct(pct) {
  return (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
}

function _typeEmoji(type) {
  const map = {
    'Aggressive Longs':  '🟢',
    'Aggressive Shorts': '🔴',
    'Short Squeeze':     '🔵',
    'Long Liquidation':  '🟠'
  };
  return map[type] ?? '⚪';
}

module.exports = { sendAlert };
