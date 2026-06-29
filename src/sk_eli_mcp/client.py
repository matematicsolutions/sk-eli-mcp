"""Async httpx client for the Slovak Slov-lex static mirror (static.slov-lex.sk) with cache.

Keyless. The index page lists an act's consolidated versions; each version is a full-text HTML
page. We keep our own backoff + cache.
"""

from __future__ import annotations

import anyio
import httpx

from .cache import HttpCache
from .citations import index_url, version_url

DEFAULT_BASE_URL = "https://static.slov-lex.sk"
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
USER_AGENT = "sk-eli-mcp/0.1.0 (+https://github.com/matematicsolutions/sk-eli-mcp)"

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3


class SlovLexClient:
    """Async client. Use as ``async with SlovLexClient() as c: ...``."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        cache: HttpCache | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._cache = cache or HttpCache()
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "sk,en"},
            follow_redirects=True,
        )

    async def __aenter__(self) -> SlovLexClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()
        self._cache.close()

    async def _get(self, url: str, *, category: str) -> str:
        cached = self._cache.get(url)
        if cached is not None and isinstance(cached, str):
            return cached
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                resp = await self._http.get(url, headers={"Accept": "text/html"})
                resp.raise_for_status()
                resp.encoding = "utf-8"
                self._cache.set(url, resp.text, ttl=HttpCache.ttl_for(category))
                return resp.text
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code not in _RETRY_STATUS or attempt == _MAX_ATTEMPTS - 1:
                    raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
            await anyio.sleep(0.5 * (2**attempt))
        assert last_exc is not None
        raise last_exc

    async def get_index(self, year: int, number: int) -> str:
        """Fetch the act's history/index page (lists consolidated versions)."""
        # base_url is configurable; build the path off it rather than the citations constant.
        url = index_url(year, number)
        if self.base_url != "https://static.slov-lex.sk":
            url = f"{self.base_url}/static/SK/ZZ/{year}/{number}/"
        return await self._get(url, category="list")

    async def get_version_html(self, year: int, number: int, version_id: str) -> str:
        """Fetch the full-text HTML of a specific version."""
        url = version_url(year, number, version_id)
        if self.base_url != "https://static.slov-lex.sk":
            url = f"{self.base_url}/static/SK/ZZ/{year}/{number}/{version_id}.html"
        return await self._get(url, category="act")
