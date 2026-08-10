# The cache every data-source client reads through.
#
# Keyed by (source, method, ticker, params_hash) with a TTL chosen per call,
# because the right TTL is a property of the data, not of the vendor: Finnhub
# serves both fundamentals (stale after a week) and news (stale after an hour).
#
# What is stored is the **raw decoded JSON** of a response, never a DataFrame or
# any other rich object. Two reasons: JSON survives a pandas upgrade, and the
# alternative — pickle — makes the cache file a code-execution vector. Clients
# cache the response and convert afterwards.
#
# SQLite rather than a file per key: expiry is a WHERE clause instead of a
# directory walk, writes are atomic, and it matches app/decisions/store.py.
# Access is synchronous even though the clients are async. The writes are
# sub-millisecond local ones in a job that runs a few times a day, so an async
# driver would be a dependency bought with no measurable return.

import hashlib
import json
import sqlite3
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Final, Literal

Source = Literal["alpaca", "finnhub", "fred"]


class NeverExpires:
    """Sentinel TTL for data that cannot change: a completed trading day's
    bars, a filing that has been made. Distinct from `None`, which would be
    indistinguishable from 'no TTL supplied'."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "NEVER_EXPIRES"


NEVER_EXPIRES: Final = NeverExpires()

Ttl = timedelta | NeverExpires

# Per the phase spec. Named here so the policy is stated once and every client
# refers to it rather than inlining a number.
FUNDAMENTALS_TTL: Final = timedelta(days=7)
NEWS_TTL: Final = timedelta(hours=1)
MACRO_TTL: Final = timedelta(days=1)
# SEC filings arrive continuously — a Form 4 is due within two business days —
# so a week-old view would miss most of what a daily run exists to notice.
FILINGS_TTL: Final = timedelta(days=1)
# Quotes and snapshots are deliberately absent: they are not cached at all.


class CacheMiss(Exception):
    """Raised when a value is absent or expired and the caller demanded a hit."""


@dataclass(frozen=True)
class CacheKey:
    source: Source
    method: str
    # Empty for calls that are not about one ticker (a FRED series, a screener
    # sweep). Empty rather than None because SQLite treats NULLs as distinct in
    # a primary key, so two NULL-ticker rows would never collide — or dedupe.
    ticker: str = ""
    params: dict[str, Any] | None = None

    @property
    def params_hash(self) -> str:
        # Sorted keys so {a,b} and {b,a} are one entry, and default=str so a
        # date or Decimal in the params does not raise on the way in.
        canonical = json.dumps(self.params or {}, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Cached:
    """A cache hit. `is_stale` is the spec's 'mark it on the response' — it is
    True only when the caller explicitly accepted stale data via
    `allow_stale`, so a stale value can never be mistaken for a fresh one."""

    value: Any
    stored_at: datetime
    is_stale: bool = False


_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    source      TEXT NOT NULL,
    method      TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    paramsHash  TEXT NOT NULL,
    payload     TEXT NOT NULL,
    storedAt    TEXT NOT NULL,
    -- NULL means never expires.
    expiresAt   TEXT,
    PRIMARY KEY (source, method, ticker, paramsHash)
);

CREATE INDEX IF NOT EXISTS entries_expiry ON entries (expiresAt);
"""


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Cache:
    """Read-through cache over the data-source clients.

    `now` is injectable so TTL behaviour is testable without sleeping.
    """

    def __init__(self, path: Path, *, now: Callable[[], datetime] = _utcnow):
        self._path = path
        self._now = now
        # A fresh clone has no .data directory; make one rather than failing.
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def get(self, key: CacheKey, *, allow_stale: bool = False) -> Cached | None:
        """Return the entry, or None on a miss.

        An expired entry is a miss unless `allow_stale=True`, in which case it
        comes back flagged `is_stale`. There is no path that returns expired
        data unflagged.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload, storedAt, expiresAt FROM entries "
                "WHERE source = ? AND method = ? AND ticker = ? AND paramsHash = ?",
                (key.source, key.method, key.ticker, key.params_hash),
            ).fetchone()

        if row is None:
            return None

        expired = row["expiresAt"] is not None and datetime.fromisoformat(
            row["expiresAt"]
        ) <= self._now()
        if expired and not allow_stale:
            return None

        return Cached(
            value=json.loads(row["payload"]),
            stored_at=datetime.fromisoformat(row["storedAt"]),
            is_stale=expired,
        )

    def put(self, key: CacheKey, value: Any, *, ttl: Ttl) -> None:
        stored_at = self._now()
        expires_at = (
            None if isinstance(ttl, NeverExpires) else (stored_at + ttl).isoformat()
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO entries "
                "(source, method, ticker, paramsHash, payload, storedAt, expiresAt) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (source, method, ticker, paramsHash) DO UPDATE SET "
                "payload = excluded.payload, storedAt = excluded.storedAt, "
                "expiresAt = excluded.expiresAt",
                (
                    key.source,
                    key.method,
                    key.ticker,
                    key.params_hash,
                    json.dumps(value),
                    stored_at.isoformat(),
                    expires_at,
                ),
            )

    async def fetch(
        self,
        key: CacheKey,
        *,
        ttl: Ttl,
        load: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Return the cached value, or call `load` and cache what it returns.

        `load` failing propagates. That is the spec's rule: a miss that fails
        upstream raises rather than quietly reaching for an expired entry.
        Serving stale data is possible, but only where a caller asks for it by
        name via `get(allow_stale=True)`, and it arrives flagged.
        """
        hit = self.get(key)
        if hit is not None:
            return hit.value

        value = await load()
        self.put(key, value, ttl=ttl)
        return value

    def purge_expired(self) -> int:
        """Drop expired rows. Nothing depends on this — it keeps the file from
        growing without bound on a machine that runs the pipeline daily."""
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM entries WHERE expiresAt IS NOT NULL AND expiresAt <= ?",
                (self._now().isoformat(),),
            )
            return cursor.rowcount


def historical_ttl(end: date, *, today: date) -> Ttl:
    """TTL for a bar window ending on `end`.

    A window that closed before today can never change, so it is cached
    permanently — the spec's first cache rule. A window touching today still
    has bars arriving, so it gets the short macro TTL and is re-fetched.
    """
    return NEVER_EXPIRES if end < today else MACRO_TTL
