"""Core API client — pure data in, pure data out.

This module has no CLI/presentation concerns and no click dependency, so an MCP
server can import PatternVistaClient and expose the same methods as tools.
"""

from typing import Any, Dict, List, Optional

import requests

from .constants import (
    DEFAULT_TIMEOUT,
    RPC_DEVIATION,
    RPC_PATTERNS,
    RPC_STRETCH,
    RPC_TICKER,
    RPC_VALIDATE,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
)


class PatternVistaError(Exception):
    """Raised for auth failures and API errors, with a human-readable message."""


class PatternVistaClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = SUPABASE_URL,
        anon_key: str = SUPABASE_ANON_KEY,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        if not api_key:
            raise PatternVistaError(
                "No API key. Run `pv config set-key <KEY>` or set "
                "PATTERN_VISTA_API_KEY. Generate a key at "
                "https://www.pattern-vista.com (Account → API keys)."
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.anon_key = anon_key
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "apikey": anon_key,
                "Authorization": f"Bearer {anon_key}",
                "Content-Type": "application/json",
            }
        )

    # -- low level -----------------------------------------------------------
    def _rpc(self, fn: str, params: Dict[str, Any]) -> Any:
        url = f"{self.base_url}/rest/v1/rpc/{fn}"
        try:
            resp = self._session.post(url, json=params, timeout=self.timeout)
        except requests.RequestException as e:
            raise PatternVistaError(f"Network error calling Pattern Vista: {e}") from e

        if resp.status_code == 200:
            return resp.json()

        # PostgREST surfaces our raise exception messages in the body.
        detail = ""
        try:
            body = resp.json()
            detail = body.get("message") or body.get("hint") or str(body)
        except ValueError:
            detail = resp.text.strip()

        if "invalid_api_key" in detail:
            raise PatternVistaError(
                "Invalid or revoked API key. Check `pv config show` or generate "
                "a new key at https://www.pattern-vista.com (Account → API keys)."
            )
        raise PatternVistaError(
            f"Pattern Vista API error (HTTP {resp.status_code}): {detail or 'unknown'}"
        )

    # -- public API ----------------------------------------------------------
    def whoami(self) -> Dict[str, Any]:
        """Validate the key and report the account + billing tier."""
        data = self._rpc(RPC_VALIDATE, {"p_api_key": self.api_key})
        # SETOF function → list of one row.
        row = data[0] if isinstance(data, list) and data else data
        if not row:
            raise PatternVistaError("Key validated but no account row returned.")
        return row

    def deviation(self, direction: str, limit: int = 20) -> Dict[str, Any]:
        """MA200 deviation ranking. direction is 'over' or 'under'."""
        if direction not in ("over", "under"):
            raise PatternVistaError("direction must be 'over' or 'under'")
        return self._rpc(
            RPC_DEVIATION,
            {"p_api_key": self.api_key, "p_direction": direction, "p_limit": limit},
        )

    def patterns(self, limit: int = 20) -> Dict[str, Any]:
        """Latest recommended K-line patterns, including hist_win_w20 (paid)."""
        return self._rpc(
            RPC_PATTERNS, {"p_api_key": self.api_key, "p_limit": limit}
        )

    def ticker(self, symbol: str) -> Dict[str, Any]:
        """Current deviation + recent patterns for a single symbol."""
        return self._rpc(
            RPC_TICKER, {"p_api_key": self.api_key, "p_ticker": symbol}
        )

    def market_stretch(self, days: int = 120) -> Dict[str, Any]:
        """Market breadth: what share of the universe closed above its MA200,
        where that sits in the recorded history, and the daily series itself.

        Not tier-gated — the same reading the public /market/stretch page gives
        away in full. The key is still sent because that is what records usage
        against the account.
        """
        return self._rpc(
            RPC_STRETCH, {"p_api_key": self.api_key, "p_days": days}
        )
