"""Pattern Vista as an MCP server — the same data the CLI serves, exposed as
tools an agent can call directly.

Why this exists as a thin layer: client.py was written with no CLI or
presentation concerns precisely so it could be reused here. Everything below is
argument plumbing and tool descriptions; not one line of it re-implements an
API call, so the CLI and the MCP server can never drift apart in what they
return.

Auth is identical to the CLI's: PATTERN_VISTA_API_KEY, or the key stored by
`pv config set-key`. In an MCP client config the environment variable is the
natural place for it:

    {
      "mcpServers": {
        "pattern-vista": {
          "command": "uvx",
          "args": ["--from", "pattern-vista[mcp]", "pattern-vista-mcp"],
          "env": { "PATTERN_VISTA_API_KEY": "pv_live_..." }
        }
      }
    }

Tiering is enforced server-side from the key, exactly as it is for the CLI and
the website — this process never decides what the caller is entitled to, it
just reports the `is_billed` flag that comes back so the agent can tell whether
it is looking at a truncated list.
"""

from typing import Any, Dict, Optional

from . import __version__
from . import config as cfg
from .client import PatternVistaClient, PatternVistaError

# The SDK renamed its server class in 2.0 (FastMCP -> MCPServer) and moved the
# module with it. Both generations expose the same surface we use — a .tool()
# decorator that derives the JSON schema from the signature, and .run() for
# stdio — so support whichever is installed rather than pinning users to one.
try:
    from mcp.server.mcpserver import MCPServer as _Server          # mcp >= 2
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as _Server          # mcp 1.x
        from mcp.server.fastmcp.exceptions import ToolError
    except ImportError as e:  # pragma: no cover - the extra is not installed
        raise SystemExit(
            "The MCP server needs the `mcp` package. Install it with:\n"
            "    pip install 'pattern-vista[mcp]'\n"
            "or run it without installing:\n"
            "    uvx --from 'pattern-vista[mcp]' pattern-vista-mcp"
        ) from e


_SERVER_KWARGS = dict(
    name="pattern-vista",
    instructions=(
        "Daily US equity technical data: MA200 deviation rankings, market "
        "breadth, and K-line chart patterns carried with their historical "
        "win-rate against SPY. Coverage is the S&P 500, the Nasdaq 100 and "
        "major US ETFs, updated once per trading day after the close — this is "
        "end-of-day data, never intraday or real-time. Call account_status "
        "first if you need to know whether the key can see full lists."
    ),
)

# An MCP client shows serverInfo.version to the user, and MCPServer defaults it
# to an empty string — so it has to be passed explicitly or every client reports
# this server as having no version. Guarded because mcp 1.x's FastMCP funnels
# unknown kwargs into a settings model and may reject it outright.
try:
    mcp = _Server(version=__version__, **_SERVER_KWARGS)
except TypeError:
    mcp = _Server(**_SERVER_KWARGS)

_client: Optional[PatternVistaClient] = None


def _get_client() -> PatternVistaClient:
    """Build the client on first use, not at import.

    A missing key must surface as an answerable tool error ("set
    PATTERN_VISTA_API_KEY"), not as a server that dies during startup
    handshake — an MCP client shows the former to the user and hides the
    latter behind "server failed to start".
    """
    global _client
    if _client is None:
        key = cfg.resolve_api_key()
        if not key:
            raise ToolError(
                "No Pattern Vista API key. Set PATTERN_VISTA_API_KEY in this "
                "server's env, or run `pv config set-key <KEY>`. Generate a key "
                "at https://www.pattern-vista.com (Account → API keys)."
            )
        _client = PatternVistaClient(key)
    return _client


def _call(fn, *args, **kwargs) -> Dict[str, Any]:
    """Turn the client's exceptions into tool errors carrying its own message.

    PatternVistaError messages are already written for a human reading them
    ("Invalid or revoked API key. Check ... or generate a new key at ..."), so
    they are exactly what an agent should relay rather than something to
    replace with a generic failure.
    """
    try:
        return fn(*args, **kwargs)
    except PatternVistaError as e:
        raise ToolError(str(e)) from e


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def market_stretch(days: int = 120) -> Dict[str, Any]:
    """How stretched the US market is: the share of tracked symbols closing
    above their own 200-day moving average, plus where that reading ranks
    against its own recorded history.

    This is a breadth (participation) measure, not an index level: a
    cap-weighted index can sit above its 200-day average while most of its
    members sit below theirs. Use it to answer "is the market broadly extended
    or broadly depressed right now", never as a forecast.

    Args:
        days: How many trading sessions of history to return, newest last.
            Capped at 1000 server-side. Use a small number if you only need the
            current reading.

    Returns:
        current: the latest session — snapshot_date, total, above_ma200,
            pct_above (0..1), median, p10, p90.
        percentile: where current.pct_above ranks in the full stored history,
            0..1, where 1.0 means the broadest participation on record.
        history: the daily series, oldest first.
    """
    return _call(_get_client().market_stretch, days=days)


@mcp.tool()
def deviation_ranking(direction: str = "under", limit: int = 20) -> Dict[str, Any]:
    """Symbols furthest from their own 200-day moving average, ranked.

    direction="under" lists the most depressed names (price far below its
    long-term average — the mean-reversion long candidates); direction="over"
    lists the most extended ones. Deviation is (close - MA200) / MA200, so
    -0.30 means the price is 30% below its own 200-day average.

    Symbols whose 200-day window contains a single-day move above 25% are
    excluded: in practice that is an unadjusted stock split rather than a real
    move, and it would otherwise dominate the ranking.

    Args:
        direction: "under" or "over".
        limit: Max rows, up to 100. Free accounts always receive 2 regardless —
            check is_billed in the response before reporting the list as
            complete.
    """
    if direction not in ("over", "under"):
        raise ToolError('direction must be "over" or "under"')
    return _call(_get_client().deviation, direction=direction, limit=limit)


@mcp.tool()
def recommended_patterns(limit: int = 20) -> Dict[str, Any]:
    """The latest K-line chart patterns the daily scan flagged, each carried
    with the historical win-rate of its own pattern bucket.

    hist_win_w20 is the share of past occurrences of that (pattern type,
    direction) bucket that beat SPY over the following 20 trading days — an
    aggregate property of the bucket, NOT a probability for this specific
    signal. Anything at or below 0.5 has no historical edge over simply holding
    the index, and several bullish buckets sit well below it; report the number
    rather than treating a flagged pattern as a recommendation.

    Args:
        limit: Max rows, up to 100. Free accounts receive 2 rows and a null
            hist_win_w20 — check is_billed before drawing conclusions from an
            empty win-rate.
    """
    return _call(_get_client().patterns, limit=limit)


@mcp.tool()
def ticker_report(symbol: str) -> Dict[str, Any]:
    """Everything held on one symbol: its current distance from its own 200-day
    moving average, and the chart patterns most recently detected on it.

    Args:
        symbol: A US ticker, e.g. "AAPL". Case-insensitive.

    Returns:
        deviation: null when the symbol is outside the covered universe (S&P
            500 / Nasdaq 100 / major US ETFs) or was filtered out of the latest
            snapshot — a null here means "not covered", not "no deviation".
        patterns: recent detections, newest first, with hist_win_w20 for paid
            keys.
    """
    sym = (symbol or "").strip()
    if not sym:
        raise ToolError("symbol is required, e.g. 'AAPL'")
    return _call(_get_client().ticker, symbol=sym)


@mcp.tool()
def account_status() -> Dict[str, Any]:
    """Validate the configured API key and report which account it belongs to
    and whether it is on a paid tier.

    Worth calling before presenting any list as complete: on a free key every
    ranking is truncated to 2 rows and pattern win-rates come back null, which
    is indistinguishable from a quiet market unless the tier is known.
    """
    return _call(_get_client().whoami)


def main() -> None:
    """Console-script entry point. Speaks MCP over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
