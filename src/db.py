"""SQLite persistence for lottery listings.

The DB file is committed back into the git repo by the GitHub Actions
workflow after each run, so it survives across ephemeral runner instances
without needing a paid hosted database.
"""
import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    store_name TEXT NOT NULL,
    apply_start TEXT,
    apply_deadline TEXT,
    result_date TEXT,
    pickup_period TEXT,
    apply_method TEXT,
    delivery_type TEXT,      -- 'online' | 'pickup' | 'unknown'
    prefecture TEXT,         -- best-effort guess, only meaningful for 'pickup'
    in_scope INTEGER NOT NULL, -- 1 if it passes the 1都3県/オンライン filter
    source_url TEXT,
    detected_at TEXT NOT NULL,
    notified_new INTEGER NOT NULL DEFAULT 0,
    notified_24h INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS source_state (
    url TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    last_checked TEXT NOT NULL
);
"""


def listing_id(product_name: str, store_name: str, apply_deadline: str) -> str:
    """Deterministic dedup key, standing in for the tweet_id we no longer have."""
    raw = f"{product_name.strip()}|{store_name.strip()}|{(apply_deadline or '').strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_existing_ids(conn) -> set[str]:
    return {row["id"] for row in conn.execute("SELECT id FROM listings")}


def insert_listing(conn, item: dict, in_scope: bool, detected_at: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO listings
            (id, product_name, store_name, apply_start, apply_deadline,
             result_date, pickup_period, apply_method, delivery_type,
             prefecture, in_scope, source_url, detected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item["id"],
            item["product_name"],
            item["store_name"],
            item.get("apply_start"),
            item.get("apply_deadline"),
            item.get("result_date"),
            item.get("pickup_period"),
            item.get("apply_method"),
            item.get("delivery_type", "unknown"),
            item.get("prefecture"),
            1 if in_scope else 0,
            item.get("source_url"),
            detected_at,
        ),
    )


def mark_notified_new(conn, listing_id_: str) -> None:
    conn.execute("UPDATE listings SET notified_new = 1 WHERE id = ?", (listing_id_,))


def mark_notified_24h(conn, listing_id_: str) -> None:
    conn.execute("UPDATE listings SET notified_24h = 1 WHERE id = ?", (listing_id_,))


def archive_past_deadline(conn, now_iso: str) -> None:
    conn.execute(
        "UPDATE listings SET archived = 1 "
        "WHERE archived = 0 AND apply_deadline IS NOT NULL AND apply_deadline < ?",
        (now_iso,),
    )


def fetch_active(conn) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM listings WHERE archived = 0 AND in_scope = 1 "
        "ORDER BY (apply_deadline IS NULL), apply_deadline ASC"
    ).fetchall()


def get_source_hash(conn, url: str) -> str | None:
    row = conn.execute(
        "SELECT content_hash FROM source_state WHERE url = ?", (url,)
    ).fetchone()
    return row["content_hash"] if row else None


def set_source_hash(conn, url: str, content_hash: str, checked_at: str) -> None:
    conn.execute(
        """
        INSERT INTO source_state (url, content_hash, last_checked)
        VALUES (?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            content_hash = excluded.content_hash,
            last_checked = excluded.last_checked
        """,
        (url, content_hash, checked_at),
    )


def fetch_needing_24h_notice(conn, now_iso: str, threshold_iso: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM listings WHERE archived = 0 AND in_scope = 1 "
        "AND notified_24h = 0 AND apply_deadline IS NOT NULL "
        "AND apply_deadline <= ? AND apply_deadline > ?",
        (threshold_iso, now_iso),
    ).fetchall()
