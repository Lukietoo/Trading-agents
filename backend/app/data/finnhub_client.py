# Finnhub: fundamentals, company news, earnings and insider transactions.
#
# Every request passes through a RateLimiter before it is made. The free tier
# allows 60 calls a minute and the pipeline sweeps many tickers, so staying
# under the limit is normal operation, not error handling.
#
# Absent fields come back as None, never 0.0 or "". Finnhub reports null for
# plenty of metrics on smaller companies, and an agent told a company's
# operating margin is zero will reason very differently from one told the
# figure is unavailable.

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Final

import httpx

from app.data.cache import FILINGS_TTL, FUNDAMENTALS_TTL, NEWS_TTL, Cache, CacheKey
from app.data.http import DEFAULT_RETRY_POLICY, RetryPolicy, get_json
from app.data.rate_limit import FINNHUB_CALLS_PER_MINUTE, RateLimiter

DEFAULT_BASE_URL: Final = "https://finnhub.io/api/v1"


@dataclass(frozen=True)
class Fundamentals:
    """The metrics an analyst agent actually reasons about, lifted out of the
    133 Finnhub returns. `raw` keeps the rest rather than discarding it, so
    reaching for an unlisted metric does not mean changing this class."""

    ticker: str
    # NOTE: Finnhub reports market cap in **millions** of USD. AAPL comes back
    # as ~4_572_794, not ~4.57e12. Anything comparing this against a price or a
    # dollar figure must scale it first.
    market_cap_millions: float | None
    pe_ttm: float | None
    peg_ttm: float | None
    price_to_book: float | None
    price_to_sales_ttm: float | None
    beta: float | None
    dividend_yield_pct: float | None
    gross_margin_ttm: float | None
    operating_margin_ttm: float | None
    net_margin_ttm: float | None
    eps_growth_ttm_yoy: float | None
    revenue_growth_ttm_yoy: float | None
    current_ratio_quarterly: float | None
    week52_high: float | None
    week52_low: float | None
    price_return_52w_pct: float | None
    raw: dict[str, Any]

    @classmethod
    def from_wire(cls, ticker: str, body: dict[str, Any]) -> "Fundamentals":
        metric = body.get("metric") or {}

        def value(name: str) -> float | None:
            # Finnhub also uses "" and "n/a" for absent numbers in places.
            raw = metric.get(name)
            return raw if isinstance(raw, (int, float)) else None

        return cls(
            ticker=ticker,
            market_cap_millions=value("marketCapitalization"),
            pe_ttm=value("peTTM"),
            peg_ttm=value("pegTTM"),
            price_to_book=value("pb"),
            price_to_sales_ttm=value("psTTM"),
            beta=value("beta"),
            dividend_yield_pct=value("currentDividendYieldTTM"),
            gross_margin_ttm=value("grossMarginTTM"),
            operating_margin_ttm=value("operatingMarginTTM"),
            net_margin_ttm=value("netProfitMarginTTM"),
            eps_growth_ttm_yoy=value("epsGrowthTTMYoy"),
            revenue_growth_ttm_yoy=value("revenueGrowthTTMYoy"),
            current_ratio_quarterly=value("currentRatioQuarterly"),
            week52_high=value("52WeekHigh"),
            week52_low=value("52WeekLow"),
            price_return_52w_pct=value("52WeekPriceReturnDaily"),
            raw=metric,
        )

    @property
    def is_populated(self) -> bool:
        """False when Finnhub knew nothing about the ticker. An unknown symbol
        returns 200 with an empty body rather than a 404, so this is the only
        way to tell 'no such company' from 'a company with no P/E'."""
        return bool(self.raw)


@dataclass(frozen=True)
class NewsItem:
    id: int
    published_at: datetime
    headline: str
    summary: str
    source: str
    url: str
    category: str

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> "NewsItem":
        return cls(
            id=raw.get("id", 0),
            # Epoch seconds on the wire.
            published_at=datetime.fromtimestamp(raw["datetime"], tz=UTC),
            headline=raw.get("headline", ""),
            summary=raw.get("summary", ""),
            source=raw.get("source", ""),
            url=raw.get("url", ""),
            category=raw.get("category", ""),
        )


@dataclass(frozen=True)
class EarningsEvent:
    date: date
    quarter: int | None
    year: int | None
    eps_actual: float | None
    eps_estimate: float | None
    revenue_actual: float | None
    revenue_estimate: float | None
    # "bmo" before market open, "amc" after market close, "" when unannounced.
    hour: str

    @property
    def is_reported(self) -> bool:
        return self.eps_actual is not None

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> "EarningsEvent":
        return cls(
            date=date.fromisoformat(raw["date"]),
            quarter=raw.get("quarter"),
            year=raw.get("year"),
            eps_actual=raw.get("epsActual"),
            eps_estimate=raw.get("epsEstimate"),
            revenue_actual=raw.get("revenueActual"),
            revenue_estimate=raw.get("revenueEstimate"),
            hour=raw.get("hour") or "",
        )


@dataclass(frozen=True)
class InsiderTx:
    name: str
    transaction_date: date | None
    filing_date: date | None
    # Signed: negative is a disposal, positive an acquisition.
    change: int
    shares_held_after: int | None
    transaction_price: float | None
    # SEC Form 4 code. "P" purchase, "S" sale, "G" gift, "M" option exercise,
    # "A" grant. Only P and S are open-market trades with a price signal —
    # counting a grant or a gift as a purchase is the classic misreading.
    transaction_code: str
    is_derivative: bool

    @property
    def is_open_market(self) -> bool:
        return self.transaction_code in {"P", "S"}

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> "InsiderTx":
        def parsed(field_name: str) -> date | None:
            value = raw.get(field_name)
            return date.fromisoformat(value) if value else None

        return cls(
            name=raw.get("name", ""),
            transaction_date=parsed("transactionDate"),
            filing_date=parsed("filingDate"),
            change=raw.get("change") or 0,
            shares_held_after=raw.get("share"),
            transaction_price=raw.get("transactionPrice"),
            transaction_code=raw.get("transactionCode") or "",
            is_derivative=bool(raw.get("isDerivative")),
        )


class FinnhubClient:
    def __init__(
        self,
        *,
        api_key: str,
        cache: Cache,
        base_url: str = DEFAULT_BASE_URL,
        limiter: RateLimiter | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        policy: RetryPolicy = DEFAULT_RETRY_POLICY,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._api_key = api_key
        self._cache = cache
        self._base_url = base_url.rstrip("/")
        self._limiter = limiter or RateLimiter(FINNHUB_CALLS_PER_MINUTE)
        self._transport = transport
        self._policy = policy
        self._now = now

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        # The limiter gates the request itself, not the cache lookup: a cache
        # hit costs Finnhub nothing and must not consume quota.
        await self._limiter.acquire()
        async with httpx.AsyncClient(transport=self._transport, timeout=30.0) as http:
            return await get_json(
                http,
                f"{self._base_url}{path}",
                params={**params, "token": self._api_key},
                policy=self._policy,
                source="finnhub",
            )

    async def get_fundamentals(self, ticker: str) -> Fundamentals:
        """Company metrics. Cached for a week — these move on a quarterly
        reporting cadence, so a shorter TTL spends quota for identical data."""
        key = CacheKey(source="finnhub", method="fundamentals", ticker=ticker)

        async def load() -> Any:
            return await self._get("/stock/metric", {"symbol": ticker, "metric": "all"})

        body = await self._cache.fetch(key, ttl=FUNDAMENTALS_TTL, load=load)
        return Fundamentals.from_wire(ticker, body or {})

    async def get_company_news(
        self, ticker: str, start: date, end: date
    ) -> list[NewsItem]:
        """Headlines in a date range, newest first. Cached an hour."""
        key = CacheKey(
            source="finnhub",
            method="company_news",
            ticker=ticker,
            params={"start": start.isoformat(), "end": end.isoformat()},
        )

        async def load() -> Any:
            return await self._get(
                "/company-news",
                {"symbol": ticker, "from": start.isoformat(), "to": end.isoformat()},
            )

        body = await self._cache.fetch(key, ttl=NEWS_TTL, load=load)
        items = [NewsItem.from_wire(row) for row in body or []]
        return sorted(items, key=lambda item: item.published_at, reverse=True)

    async def get_earnings_calendar(
        self, ticker: str, start: date, end: date
    ) -> list[EarningsEvent]:
        """Past and scheduled earnings dates, chronological.

        The window is explicit rather than defaulted because "upcoming
        earnings" means something different to a screener looking days ahead
        and to an evaluation pass looking quarters back.
        """
        key = CacheKey(
            source="finnhub",
            method="earnings_calendar",
            ticker=ticker,
            params={"start": start.isoformat(), "end": end.isoformat()},
        )

        async def load() -> Any:
            return await self._get(
                "/calendar/earnings",
                {"symbol": ticker, "from": start.isoformat(), "to": end.isoformat()},
            )

        body = await self._cache.fetch(key, ttl=FUNDAMENTALS_TTL, load=load)
        events = [
            EarningsEvent.from_wire(row)
            for row in (body or {}).get("earningsCalendar") or []
        ]
        return sorted(events, key=lambda event: event.date)

    async def get_insider_transactions(
        self, ticker: str, start: date, end: date
    ) -> list[InsiderTx]:
        """Form 4 filings, newest first.

        Cached a day rather than a week: filings arrive continuously, and a
        week-old view of insider activity would miss most of what a daily run
        exists to notice.
        """
        key = CacheKey(
            source="finnhub",
            method="insider_transactions",
            ticker=ticker,
            params={"start": start.isoformat(), "end": end.isoformat()},
        )

        async def load() -> Any:
            return await self._get(
                "/stock/insider-transactions",
                {"symbol": ticker, "from": start.isoformat(), "to": end.isoformat()},
            )

        body = await self._cache.fetch(key, ttl=FILINGS_TTL, load=load)
        transactions = [InsiderTx.from_wire(row) for row in (body or {}).get("data") or []]
        return sorted(
            transactions,
            key=lambda tx: tx.filing_date or date.min,
            reverse=True,
        )
