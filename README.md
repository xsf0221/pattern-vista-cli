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

The `PatternVistaClient` core has no CLI dependency, so it can back an MCP server
exposing the same methods as tools.

## Data notes

- **Deviation** = `(close − MA200) / MA200`, refreshed nightly over an S&P 500 +
  Nasdaq 100 + major-ETF universe. Split-distorted and implausible values are
  filtered out before ranking.
- **Win-rate** (`hist_win_w20`) is the historical 20-trading-day hit rate of a
  pattern type since 2025-01-01. See the methodology post at
  <https://www.pattern-vista.com/posts/pattern-alpha-backtest>.
- Past performance does not guarantee future results. Not investment advice.

## License

MIT
