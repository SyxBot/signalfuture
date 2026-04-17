import json
import os
import sqlite3
import time
from typing import Optional

from models.smart_money import SmartMoneyWallet
from models.token_card import SmartMoneySignal, TokenCard

DDL = """
CREATE TABLE IF NOT EXISTS tokens (
    mint        TEXT PRIMARY KEY,
    data_json   TEXT NOT NULL,
    source      TEXT,
    fetched_at  REAL NOT NULL,
    security_json TEXT,
    security_ts   REAL
);

CREATE TABLE IF NOT EXISTS wallets (
    address     TEXT PRIMARY KEY,
    data_json   TEXT NOT NULL,
    fetched_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS smart_money_links (
    mint           TEXT NOT NULL,
    wallet_address TEXT NOT NULL,
    signal_json    TEXT NOT NULL,
    created_at     REAL NOT NULL,
    PRIMARY KEY (mint, wallet_address)
);
"""


class SQLiteCache:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(DDL)
        self._conn.commit()

    # ── tokens ──────────────────────────────────────────────────────────────

    def upsert_token(self, card: TokenCard) -> None:
        self._conn.execute(
            """
            INSERT INTO tokens (mint, data_json, source, fetched_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(mint) DO UPDATE SET
                data_json  = excluded.data_json,
                source     = excluded.source,
                fetched_at = excluded.fetched_at
            """,
            (card.mint, card.model_dump_json(), card.source, time.time()),
        )
        self._conn.commit()

    def get_token(self, mint: str) -> Optional[TokenCard]:
        row = self._conn.execute(
            "SELECT data_json FROM tokens WHERE mint = ?", (mint,)
        ).fetchone()
        if row is None:
            return None
        card = TokenCard.model_validate_json(row["data_json"])
        return self._attach_sm_signals(card)

    def get_all_tokens(self, limit: int = 200) -> list[TokenCard]:
        rows = self._conn.execute(
            "SELECT data_json, mint FROM tokens ORDER BY fetched_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._attach_sm_signals(TokenCard.model_validate_json(r["data_json"])) for r in rows]

    def get_recent_mints(self, limit: int = 20) -> list[str]:
        rows = self._conn.execute(
            "SELECT mint FROM tokens ORDER BY fetched_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [r["mint"] for r in rows]

    # ── security overlay ────────────────────────────────────────────────────

    def get_security(self, mint: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT security_json, security_ts FROM tokens WHERE mint = ?", (mint,)
        ).fetchone()
        if row is None or not row["security_json"]:
            return None
        if time.time() - (row["security_ts"] or 0) > 300:
            return None
        return json.loads(row["security_json"])

    def set_security(self, mint: str, sec: dict, ttl: int = 300) -> None:
        self._conn.execute(
            """
            UPDATE tokens SET security_json = ?, security_ts = ?
            WHERE mint = ?
            """,
            (json.dumps(sec), time.time(), mint),
        )
        self._conn.commit()

    # ── wallets ─────────────────────────────────────────────────────────────

    def get_wallet(self, address: str, ttl: int = 600) -> Optional[SmartMoneyWallet]:
        row = self._conn.execute(
            "SELECT data_json, fetched_at FROM wallets WHERE address = ?", (address,)
        ).fetchone()
        if row is None:
            return None
        if time.time() - row["fetched_at"] > ttl:
            return None
        return SmartMoneyWallet.model_validate_json(row["data_json"])

    def set_wallet(self, wallet: SmartMoneyWallet, ttl: int = 600) -> None:
        self._conn.execute(
            """
            INSERT INTO wallets (address, data_json, fetched_at)
            VALUES (?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                data_json  = excluded.data_json,
                fetched_at = excluded.fetched_at
            """,
            (wallet.address, wallet.model_dump_json(), time.time()),
        )
        self._conn.commit()

    def get_all_wallets(self, limit: int = 50) -> list[SmartMoneyWallet]:
        rows = self._conn.execute(
            "SELECT data_json FROM wallets ORDER BY fetched_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [SmartMoneyWallet.model_validate_json(r["data_json"]) for r in rows]

    # ── smart money links ───────────────────────────────────────────────────

    def attach_smart_money(self, mint: str, signal: SmartMoneySignal) -> None:
        self._conn.execute(
            """
            INSERT INTO smart_money_links (mint, wallet_address, signal_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(mint, wallet_address) DO UPDATE SET
                signal_json = excluded.signal_json,
                created_at  = excluded.created_at
            """,
            (mint, signal.wallet_address, signal.model_dump_json(), time.time()),
        )
        self._conn.commit()

    def _get_sm_signals(self, mint: str, ttl: int = 120) -> list[SmartMoneySignal]:
        cutoff = time.time() - ttl
        rows = self._conn.execute(
            "SELECT signal_json FROM smart_money_links WHERE mint = ? AND created_at > ?",
            (mint, cutoff),
        ).fetchall()
        return [SmartMoneySignal.model_validate_json(r["signal_json"]) for r in rows]

    def _attach_sm_signals(self, card: TokenCard) -> TokenCard:
        signals = self._get_sm_signals(card.mint)
        if not signals:
            return card
        return card.model_copy(update={
            "smart_money_buyers": signals,
            "smart_money_count": len(signals),
        })

    def close(self) -> None:
        self._conn.close()
