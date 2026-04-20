'use strict';

require('dotenv').config();

const EventEmitter = require('events');
const { BinanceFeedManager, DEFAULT_SYMBOLS } = require('./src/feeds/binanceWS');
const { OpenInterestTracker }  = require('./src/feeds/openInterest');
const { SpikeDetector }        = require('./src/detectors/spikeDetector');
const { buildSignal }          = require('./src/signals/classifier');
const { scoreSignal, isAboveThreshold } = require('./src/scoring/scorer');
const { SignalStorage }        = require('./src/storage/db');
const { createServer }         = require('./src/api/server');
const { sendAlert }            = require('./src/utils/telegram');
const log                      = require('./src/utils/logger');

// ── Configuration ─────────────────────────────────────────────────────────────
const PORT           = parseInt(process.env.PORT)           || 3000;
const SPIKE_THRESHOLD = parseFloat(process.env.SPIKE_THRESHOLD) || 3.0;
const SCORE_THRESHOLD = parseFloat(process.env.SCORE_THRESHOLD) || 2.0;
const VOLUME_WINDOW   = parseInt(process.env.VOLUME_WINDOW)     || 20;
const COOLDOWN_MS     = parseInt(process.env.COOLDOWN_MS)       || 120_000;
const DB_PATH         = process.env.SQLITE_PATH || './data/signals.db';

const symbols = process.env.SYMBOLS
  ? process.env.SYMBOLS.split(',').map(s => s.trim().toUpperCase()).filter(Boolean)
  : DEFAULT_SYMBOLS;

// ── Bootstrap ─────────────────────────────────────────────────────────────────
const signalBus = new EventEmitter();
signalBus.setMaxListeners(50);

const feed     = new BinanceFeedManager(symbols);
const oiTracker = new OpenInterestTracker(symbols);
const detector  = new SpikeDetector({ threshold: SPIKE_THRESHOLD, windowSize: VOLUME_WINDOW, cooldownMs: COOLDOWN_MS });
const storage   = new SignalStorage(DB_PATH);

// ── Feed event wiring ─────────────────────────────────────────────────────────
feed.on('kline', (klineEvent) => {
  const spike = detector.process(klineEvent);
  if (!spike) return;

  const oi      = oiTracker.getDelta(spike.symbol, spike.price);
  const signal  = buildSignal(spike, oi);
  const scored  = scoreSignal(signal);

  if (!isAboveThreshold(scored, SCORE_THRESHOLD)) return;

  storage.insert(scored);
  signalBus.emit('signal', scored);

  log.info(
    `[signal] ${scored.symbol.padEnd(10)} | ${scored.type.padEnd(20)} | ` +
    `score=${scored.score} vol=${scored.volumeMultiple}x ` +
    `price=${scored.priceChangePct > 0 ? '+' : ''}${scored.priceChangePct}% ` +
    `oi=${scored.oiDeltaPct > 0 ? '+' : ''}${scored.oiDeltaPct}%`
  );

  sendAlert(scored).catch(err => log.error('[telegram]', err.message));
});

feed.on('liquidation', (order) => {
  // Available for future use — e.g. spike context enrichment
  log.debug('[liq]', order.s, order.S, order.q, '@', order.p);
});

feed.on('connected',    (stream) => log.info(`[feed] ${stream} stream connected`));
feed.on('disconnected', (stream, code) => log.warn(`[feed] ${stream} disconnected (${code})`));
feed.on('error',        (err) => log.error('[feed]', err.message));

// ── Start ─────────────────────────────────────────────────────────────────────
async function main() {
  log.info('[boot]', `ZookAgent v2 — tracking ${symbols.length} symbols`);
  log.info('[boot]', `Spike threshold: ${SPIKE_THRESHOLD}×  Score threshold: ${SCORE_THRESHOLD}`);

  // Warm up OI cache before accepting WebSocket data
  log.info('[boot]', 'Fetching initial open interest...');
  await oiTracker.start();
  log.info('[boot]', 'OI data ready');

  // Open WebSocket feeds
  feed.start();

  // Start HTTP server
  const app = createServer(storage, signalBus);
  app.listen(PORT, () => {
    log.info('[boot]', `Server listening on http://localhost:${PORT}`);
    log.info('[boot]', `Dashboard → http://localhost:${PORT}`);
  });
}

main().catch(err => {
  log.error('[boot] Fatal startup error:', err);
  process.exit(1);
});
