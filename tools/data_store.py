"""SQLite data persistence layer for trader profiles and run history."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import structlog

from config.settings import settings
from models.trader import TraderProfile

logger = structlog.get_logger(__name__)


class DataStore:
    """SQLite persistence layer for trader data and pipeline runs.

    Auto-creates tables on first use. Uses synchronous sqlite3
    (adequate for this use case).

    Storage: data/predictions.db
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or settings.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traders (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    wallet_or_username TEXT NOT NULL,
                    display_name TEXT,
                    total_pnl REAL DEFAULT 0,
                    total_volume REAL DEFAULT 0,
                    num_trades INTEGER DEFAULT 0,
                    num_wins INTEGER DEFAULT 0,
                    composite_score REAL DEFAULT 0,
                    trust_score REAL DEFAULT 50,
                    niches TEXT DEFAULT '{}',
                    category TEXT DEFAULT 'GENERAL',
                    data_source TEXT DEFAULT 'api',
                    first_seen TEXT,
                    last_updated TEXT,
                    UNIQUE(platform, wallet_or_username)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    trader_count INTEGER,
                    top_score REAL,
                    top_trader TEXT,
                    recommendation TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.commit()
        logger.info("datastore_ready", path=str(self.db_path))

    def _connect(self) -> sqlite3.Connection:
        """Create a database connection."""
        return sqlite3.connect(str(self.db_path))

    def save_traders(self, traders: list[TraderProfile]):
        """Persist trader profiles to the database.

        Uses INSERT OR REPLACE to handle updates.

        Args:
            traders: List of TraderProfile objects to save.
        """
        with self._connect() as conn:
            for t in traders:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO traders
                    (id, platform, wallet_or_username, display_name,
                     total_pnl, total_volume, num_trades, num_wins,
                     composite_score, trust_score, niches, category,
                     data_source, first_seen, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        t.id, t.platform, t.wallet_or_username, t.display_name,
                        t.total_pnl, t.total_volume, t.num_trades, t.num_wins,
                        t.composite_score, t.trust_score,
                        json.dumps(t.niches), t.category,
                        t.data_source,
                        t.first_seen.isoformat(),
                        t.last_updated.isoformat(),
                    ),
                )
            conn.commit()
        logger.info("traders_saved", count=len(traders))

    def get_trader(self, wallet_or_username: str) -> TraderProfile | None:
        """Retrieve a cached trader by wallet/username.

        Args:
            wallet_or_username: The trader identifier.

        Returns:
            TraderProfile or None if not found.
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM traders WHERE wallet_or_username = ?",
                (wallet_or_username,),
            ).fetchone()

        if row:
            return self._row_to_trader(row)
        return None

    def get_all_traders(
        self, platform: str | None = None, limit: int = 50
    ) -> list[TraderProfile]:
        """List cached traders.

        Args:
            platform: Optional platform filter (polymarket, kalshi).
            limit: Max results.

        Returns:
            List of TraderProfile objects.
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if platform:
                rows = conn.execute(
                    "SELECT * FROM traders WHERE platform = ? ORDER BY composite_score DESC LIMIT ?",
                    (platform, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM traders ORDER BY composite_score DESC LIMIT ?",
                    (limit,),
                ).fetchall()

        return [self._row_to_trader(r) for r in rows]

    def save_run_log(
        self,
        traders: list[TraderProfile],
        recommendation: str,
        metadata: dict | None = None,
    ):
        """Log a pipeline run.

        Args:
            traders: The traders from this run.
            recommendation: The generated recommendation.
            metadata: Additional run metadata.
        """
        top = traders[0] if traders else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO run_logs (timestamp, trader_count, top_score, top_trader, recommendation, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    len(traders),
                    top.composite_score if top else 0,
                    (top.display_name or top.wallet_or_username) if top else "",
                    recommendation[:2000],
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
        logger.info("run_log_saved", trader_count=len(traders))

    def get_run_history(self, n: int = 10) -> list[dict]:
        """Retrieve past run logs.

        Args:
            n: Number of runs to retrieve.

        Returns:
            List of run log dicts.
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM run_logs ORDER BY id DESC LIMIT ?",
                (n,),
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _row_to_trader(row) -> TraderProfile:
        """Convert a SQLite row to a TraderProfile."""
        niches = json.loads(row["niches"]) if row["niches"] else {}
        return TraderProfile(
            id=row["id"],
            platform=row["platform"],
            wallet_or_username=row["wallet_or_username"],
            display_name=row["display_name"],
            total_pnl=row["total_pnl"],
            total_volume=row["total_volume"],
            num_trades=row["num_trades"],
            num_wins=row["num_wins"],
            composite_score=row["composite_score"],
            trust_score=row["trust_score"],
            niches=niches,
            category=row["category"] or "GENERAL",
            data_source=row["data_source"],
        )
