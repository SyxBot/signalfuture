'use strict';

const LEVELS = { debug: 0, info: 1, warn: 2, error: 3 };

function _level() {
  return LEVELS[process.env.LOG_LEVEL] ?? LEVELS.info;
}

function _log(level, tag, ...args) {
  if (LEVELS[level] < _level()) return;
  const ts = new Date().toISOString().slice(11, 23); // HH:MM:SS.mmm
  const line = `${ts} [${level.toUpperCase().padEnd(5)}] ${tag}`;
  if (level === 'error') {
    console.error(line, ...args);
  } else {
    console.log(line, ...args);
  }
}

module.exports = {
  debug: (tag, ...a) => _log('debug', tag, ...a),
  info:  (tag, ...a) => _log('info',  tag, ...a),
  warn:  (tag, ...a) => _log('warn',  tag, ...a),
  error: (tag, ...a) => _log('error', tag, ...a)
};
