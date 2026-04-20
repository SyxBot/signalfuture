'use strict';

const express = require('express');
const path = require('path');

/**
 * Creates and returns the Express app.
 *
 * @param {import('../storage/db').SignalStorage} storage
 * @param {import('events').EventEmitter} signalBus  emits 'signal' with each new scored signal
 * @returns {import('express').Application}
 */
function createServer(storage, signalBus) {
  const app = express();
  app.use(express.json());
  app.use(express.static(path.join(__dirname, '../../public')));

  // ── SSE client registry ──────────────────────────────────────────────────
  const sseClients = new Set();

  signalBus.on('signal', (signal) => {
    if (sseClients.size === 0) return;
    const chunk = `data: ${JSON.stringify(signal)}\n\n`;
    for (const res of sseClients) {
      try { res.write(chunk); } catch (_) { sseClients.delete(res); }
    }
  });

  // ── REST endpoints ────────────────────────────────────────────────────────

  /** Latest N signals ordered by time. */
  app.get('/signals', (req, res) => {
    const limit = Math.min(parseInt(req.query.limit) || 50, 200);
    res.json(storage.getLatest(limit));
  });

  /** Top-scoring signals from the last hour. */
  app.get('/top', (req, res) => {
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);
    res.json(storage.getTop(limit));
  });

  /** Historical signals. ?hours=N  (default 24, max 168) */
  app.get('/history', (req, res) => {
    const hours = Math.min(parseInt(req.query.hours) || 24, 168);
    res.json(storage.getHistory(hours));
  });

  // ── SSE stream endpoint ───────────────────────────────────────────────────
  app.get('/stream', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no'); // disable nginx buffering on Replit
    res.flushHeaders();

    // Send recent signals immediately so the UI isn't blank on connect
    const bootstrap = storage.getLatest(20);
    for (const s of bootstrap.reverse()) {
      res.write(`data: ${JSON.stringify(s)}\n\n`);
    }

    sseClients.add(res);

    // Keep-alive heartbeat every 25s (proxies drop idle connections at 30s)
    const heartbeat = setInterval(() => {
      try { res.write(': ping\n\n'); } catch (_) {}
    }, 25_000);

    req.on('close', () => {
      sseClients.delete(res);
      clearInterval(heartbeat);
    });
  });

  // ── Health check ──────────────────────────────────────────────────────────
  app.get('/health', (_req, res) => {
    res.json({ ok: true, sseClients: sseClients.size, ts: Date.now() });
  });

  return app;
}

module.exports = { createServer };
