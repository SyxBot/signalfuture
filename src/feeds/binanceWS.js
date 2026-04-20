'use strict';

const WebSocket = require('ws');
const EventEmitter = require('events');

const FSTREAM_BASE = 'wss://fstream.binance.com';

const DEFAULT_SYMBOLS = [
  'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
  'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT',
  'NEARUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT', 'APTUSDT',
  'ARBUSDT', 'OPUSDT', 'INJUSDT', 'SUIUSDT', 'WLDUSDT'
];

class BinanceFeedManager extends EventEmitter {
  constructor(symbols = DEFAULT_SYMBOLS) {
    super();
    this.symbols = symbols;
    this._klineWs = null;
    this._liqWs = null;
    this._klineReconnectDelay = 1000;
    this._liqReconnectDelay = 1000;
    this._stopped = false;
  }

  start() {
    this._stopped = false;
    this._connectKlineStream();
    this._connectLiquidationStream();
  }

  stop() {
    this._stopped = true;
    if (this._klineWs) this._klineWs.terminate();
    if (this._liqWs) this._liqWs.terminate();
  }

  _connectKlineStream() {
    if (this._stopped) return;

    const streams = this.symbols
      .map(s => `${s.toLowerCase()}@kline_1m`)
      .join('/');
    const url = `${FSTREAM_BASE}/stream?streams=${streams}`;

    const ws = new WebSocket(url);
    this._klineWs = ws;

    ws.on('open', () => {
      this._klineReconnectDelay = 1000;
      this.emit('connected', 'kline');
    });

    ws.on('message', (raw) => {
      try {
        const msg = JSON.parse(raw);
        // Combined stream wraps payload in { stream, data }
        const event = msg.data || msg;
        if (event.e === 'kline') this.emit('kline', event);
      } catch (_) {}
    });

    ws.on('close', (code) => {
      this.emit('disconnected', 'kline', code);
      if (!this._stopped) {
        setTimeout(() => this._connectKlineStream(), this._klineReconnectDelay);
        this._klineReconnectDelay = Math.min(this._klineReconnectDelay * 2, 30000);
      }
    });

    ws.on('error', (err) => {
      this.emit('error', new Error(`[kline] ${err.message}`));
    });
  }

  _connectLiquidationStream() {
    if (this._stopped) return;

    const url = `${FSTREAM_BASE}/ws/!forceOrder@arr`;
    const ws = new WebSocket(url);
    this._liqWs = ws;

    ws.on('open', () => {
      this._liqReconnectDelay = 1000;
      this.emit('connected', 'liquidation');
    });

    ws.on('message', (raw) => {
      try {
        const msg = JSON.parse(raw);
        if (msg.e === 'forceOrder' && msg.o) {
          this.emit('liquidation', msg.o);
        }
      } catch (_) {}
    });

    ws.on('close', (code) => {
      this.emit('disconnected', 'liquidation', code);
      if (!this._stopped) {
        setTimeout(() => this._connectLiquidationStream(), this._liqReconnectDelay);
        this._liqReconnectDelay = Math.min(this._liqReconnectDelay * 2, 30000);
      }
    });

    ws.on('error', (err) => {
      this.emit('error', new Error(`[liquidation] ${err.message}`));
    });
  }
}

module.exports = { BinanceFeedManager, DEFAULT_SYMBOLS };
