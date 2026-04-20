'use strict';

const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');

const DEFAULT_PATH = path.join(__dirname, '../../data/signals.db');

class SignalStorage {
  constructor(dbPath = DEFAULT_PATH) {
    const dir = path.dirname(dbPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    this.db = new Database(dbPath);
    this.db.pragma('journal_mode = WAL');  // better concurrent read performance
    this.db.pragma('synchronous = NORMAL');
    this._init();
  }

  _init() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS signals (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol          TEXT    NOT NULL,
        timestamp       INTEGER NOT NULL,
        price           REAL,
        volume_multiple REAL,
        price_change_pct REAL,
        oi_delta_usd    REAL,
        oi_delta_pct    REAL,
        type            TEXT,
        score           REAL,
        data_json       TEXT    NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_ts    ON signals (timestamp DESC);
      CREATE INDEX IF NOT EXISTS idx_score ON signals (score     DESC);
      CREATE INDEX IF NOT EXISTS idx_sym   ON signals (symbol);
    `);

    // Prepared statements — compiled once, reused on every insert/query
    this._insertStmt = this.db.prepare(`
      INSERT INTO signals
        (symbol, timestamp, price, volume_multiple, price_change_pct,
         oi_delta_usd, oi_delta_pct, type, score, data_json)
      VALUES
        (@symbol, @timestamp, @price, @volumeMultiple, @priceChangePct,
         @oiDeltaUsd, @oiDeltaPct, @type, @score, @data_json)
    `);

    this._latestStmt = this.db.prepare(`
      SELECT data_json FROM signals
      ORDER BY timestamp DESC
      LIMIT ?
    `);

    this._topStmt = this.db.prepare(`
      SELECT data_json FROM signals
      WHERE timestamp > ?
      ORDER BY score DESC
      LIMIT ?
    `);

    this._historyStmt = this.db.prepare(`
      SELECT data_json FROM signals
      WHERE timestamp > ?
      ORDER BY timestamp DESC
      LIMIT 500
    `);
  }

  insert(signal) {
    this._insertStmt.run({
      ...signal,
      data_json: JSON.stringify(signal)
    });
  }

  /** Latest N signals ordered by time (newest first). */
  getLatest(limit = 50) {
    return this._latestStmt.all(limit).map(r => JSON.parse(r.data_json));
  }

  /** Highest-scoring signals from the last hour. */
  getTop(limit = 20) {
    const since = Date.now() - 3_600_000;
    return this._topStmt.all(since, limit).map(r => JSON.parse(r.data_json));
  }

  /** All signals within the last `hours` hours (max 500). */
  getHistory(hours = 24) {
    const since = Date.now() - hours * 3_600_000;
    return this._historyStmt.all(since).map(r => JSON.parse(r.data_json));
  }
}

module.exports = { SignalStorage };
