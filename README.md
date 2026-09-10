<!-- mcp-name: io.github.xsf0221/pattern-vista -->

# Pattern Vista CLI

Command-line access to [Pattern Vista](https://www.pattern-vista.com) — K-line
pattern historical win-rates and MA200 deviation rankings — built to be called
by **AI agents** as easily as by humans.

Output is **JSON by default** (so an agent can parse it directly); add `--table`
for a human-readable view.

## Install

```bash
pip install pattern-vista     # or: uvx pattern-vista whoami
```

## Authenticate

Generate a key at <https://www.pattern-vista.com> (Account → API keys), then:

```bash
pv config set-key pv_live_xxxxxxxx
# or, for ephemeral/agent use:
export PATTERN_VISTA_API_KEY=pv_live_xxxxxxxx
```

Resolution order: `--api-key` flag → `PATTERN_VISTA_API_KEY` → stored config.

## Commands

```bash
pv whoami                       # validate key, show account + tier
pv deviation --over --limit 20  # stocks furthest ABOVE their 200-day average
pv deviation --under            # stocks furthest BELOW (mean-reversion longs)
pv patterns --limit 20          # latest recommended patterns + 20-day win-rate
pv ticker AAPL                  # one symbol: current deviation + recent patterns
pv stretch --days 120           # market breadth: % of the universe above its MA200

# add --table to any command for human output:
pv deviation --under --table
```

### Example (agent-friendly JSON)

```bash
$ pv deviation --under --limit 3
{
  "is_billed": true,
  "rows": [
    {"ticker": "XYZ", "snapshot_date": "2026-05-27", "close": 41.2, "ma200": 58.9, "deviation": -0.3005},
    ...
  ]
}
```

## Free vs. paid

A free account sees the **top 2** rows of each list and patterns without the
historical win-rate. A paid subscription unlocks the full lists (up to 100) and
`hist_win_w20`. The tier is enforced server-side from the key — see
`is_billed` in every response.

## For agents / programmatic use

```python
from pattern_vista import PatternVistaClient

pv = PatternVistaClient(api_key="pv_live_xxxx")
under = pv.deviation("under", limit=20)   # dict: {"is_billed": ..., "rows": [...]}
aapl = pv.ticker("AAPL")
```

The `PatternVistaClient` core has no CLI dependency — it is what backs the MCP
server below, so the two can never return different things.

## Use as an MCP server

The same data as tools your agent can call directly. No install needed if you
have `uv`:

```jsonc
{
  "mcpServers": {
    "pattern-vista": {
      "command": "uvx",
      "args": ["--from", "pattern-vista[mcp]", "pattern-vista-mcp"],
      "env": { "PATTERN_VISTA_API_KEY": "pv_live_xxxxxxxx" }
    }
  }
}
```

Drop that into your MCP client's config (Claude Desktop, Claude Code, Cursor,
or anything else that speaks MCP over stdio). If you would rather install it:

```bash
pip install 'pattern-vista[mcp]'   # then use "command": "pattern-vista-mcp"
```

Or run it in a container. `-i` is required — the transport is stdio, so without
an attached stdin the server has nothing to read and exits straight away:

```bash
docker build -t pattern-vista-mcp .
docker run -i --rm -e PATTERN_VISTA_API_KEY=pv_live_xxxxxxxx pattern-vista-mcp
```

### Tools

| Tool | Answers |
|---|---|
| `market_stretch` | Is the market broadly extended or depressed right now, and how does that rank against its own history? |
| `deviation_ranking` | Which symbols are furthest below (or above) their own 200-day average? |
| `recommended_patterns` | What did last night's scan flag, and has that pattern bucket historically beaten SPY? |
| `ticker_report` | Everything held on one symbol. |
| `account_status` | Which account is this key, and is it on a paid tier? |

Auth resolves exactly as the CLI's does: `PATTERN_VISTA_API_KEY`, else the key
saved by `pv config set-key`. Tiering stays server-side — a free key gets 2 rows
and a null `hist_win_w20`, so check `is_billed` in the response before treating
a short list as a quiet market.

Works with both generations of the MCP Python SDK (`mcp` 1.x's `FastMCP` and
2.x's `MCPServer`).

## Data notes

- **Deviation** = `(close − MA200) / MA200`, refreshed nightly over an S&P 500 +
  Nasdaq 100 + major-ETF universe. Split-distorted and implausible values are
  filtered out before ranking.
- **Market breadth** (`pv stretch`, `market_stretch`) is the share of that same
  universe closing above its own MA200, one reading per trading day, with the
  history behind it. Free for every tier — it is the same number the public
  page at <https://www.pattern-vista.com/market/stretch> publishes.
- **Win-rate** (`hist_win_w20`) is the historical 20-trading-day hit rate of a
  pattern type since 2025-01-01. See the methodology post at
  <https://www.pattern-vista.com/posts/pattern-alpha-backtest>.
- Past performance does not guarantee future results. Not investment advice.

## License

MIT
