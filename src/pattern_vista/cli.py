"""Click command layer — thin presentation over PatternVistaClient."""

import sys
from typing import Optional

import click

from . import __version__
from . import config as cfg
from . import formatting as fmt
from .client import PatternVistaClient, PatternVistaError
from .constants import API_KEY_ENV


def _client(api_key: Optional[str]) -> PatternVistaClient:
    key = cfg.resolve_api_key(api_key)
    return PatternVistaClient(key or "")


def _emit_rows(payload: dict, columns, headers, *, table: bool, transform=None) -> None:
    """payload is {is_billed, rows}. Print JSON or an ASCII table."""
    if not table:
        click.echo(fmt.as_json(payload))
        return
    rows = payload.get("rows", []) if isinstance(payload, dict) else payload
    view = [transform(r) for r in rows] if transform else rows
    click.echo(fmt.table(view, columns, headers))
    if isinstance(payload, dict) and not payload.get("is_billed", True):
        click.echo(
            "\nFree tier: showing top 2 only. Upgrade for the full list → "
            "https://www.pattern-vista.com/pricing"
        )


# -----------------------------------------------------------------------------
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="pattern-vista")
@click.option("--api-key", envvar=API_KEY_ENV, help="Override the stored API key.")
@click.pass_context
def cli(ctx: click.Context, api_key: Optional[str]):
    """Pattern Vista — pattern win-rates and MA200 deviation rankings from the terminal.

    Output is JSON by default (agent-friendly); add --table for a human view.
    """
    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key


# -- config -------------------------------------------------------------------
@cli.group()
def config():
    """Manage the stored API key."""


@config.command("set-key")
@click.argument("key")
def config_set_key(key: str):
    """Store KEY in ~/.config/pattern-vista/config.json (owner-readable only)."""
    path = cfg.set_api_key(key)
    click.echo(f"Saved API key to {path}")


@config.command("show")
def config_show():
    """Show where the key resolves from and a masked preview."""
    key = cfg.resolve_api_key()
    if not key:
        click.echo("No API key configured. Run `pv config set-key <KEY>`.")
        return
    masked = key[:12] + "…" + key[-4:] if len(key) > 18 else "set"
    click.echo(f"api_key: {masked}\nconfig:  {cfg.config_path()}")


# -- account ------------------------------------------------------------------
@cli.command()
@click.option("--table", is_flag=True, help="Human-readable instead of JSON.")
@click.pass_context
def whoami(ctx, table: bool):
    """Validate the API key and show account + billing tier."""
    info = _client(ctx.obj["api_key"]).whoami()
    if table:
        tier = "paid" if info.get("is_billed") else "free"
        click.echo(f"email: {info.get('email')}\ntier:  {tier}")
    else:
        click.echo(fmt.as_json(info))


# -- deviation ----------------------------------------------------------------
@cli.command()
@click.option("--over", "direction", flag_value="over", default=True,
              help="Stocks furthest ABOVE their MA200 (default).")
@click.option("--under", "direction", flag_value="under",
              help="Stocks furthest BELOW their MA200.")
@click.option("--limit", default=20, show_default=True, help="Max rows (paid).")
@click.option("--table", is_flag=True, help="Human-readable instead of JSON.")
@click.pass_context
def deviation(ctx, direction: str, limit: int, table: bool):
    """MA200 deviation ranking: (close − MA200) / MA200."""
    payload = _client(ctx.obj["api_key"]).deviation(direction, limit)
    _emit_rows(
        payload,
        columns=["ticker", "close", "ma200", "deviation"],
        headers=["TICKER", "CLOSE", "MA200", "DEV"],
        table=table,
        transform=lambda r: {**r, "deviation": fmt.pct(r.get("deviation"))},
    )


# -- stretch ------------------------------------------------------------------
@cli.command()
@click.option("--days", default=120, show_default=True,
              help="Sessions of history to fetch (max 1000).")
@click.option("--table", is_flag=True, help="Human-readable instead of JSON.")
@click.pass_context
def stretch(ctx, days: int, table: bool):
    """Market breadth: share of the universe closing above its own MA200."""
    payload = _client(ctx.obj["api_key"]).market_stretch(days)
    if not table:
        click.echo(fmt.as_json(payload))
        return

    cur = payload.get("current") or {}
    if not cur:
        click.echo("No breadth snapshot available yet.")
        return
    pctile = payload.get("percentile")
    click.echo(
        f"{cur.get('snapshot_date')}  "
        f"{fmt.pct(cur.get('pct_above'))} of {cur.get('total')} names above their MA200"
    )
    click.echo(f"median stretch: {fmt.pct(cur.get('median'))}")
    if pctile is not None:
        click.echo(f"percentile vs history: {fmt.pct(pctile)}")
    hist = payload.get("history") or []
    if hist:
        click.echo(f"history: {hist[0].get('snapshot_date')} → "
                   f"{hist[-1].get('snapshot_date')} ({len(hist)} sessions)")


# -- patterns -----------------------------------------------------------------
@cli.command()
@click.option("--limit", default=20, show_default=True, help="Max rows (paid).")
@click.option("--table", is_flag=True, help="Human-readable instead of JSON.")
@click.pass_context
def patterns(ctx, limit: int, table: bool):
    """Latest recommended K-line patterns, with historical 20-day win-rate (paid)."""
    payload = _client(ctx.obj["api_key"]).patterns(limit)
    _emit_rows(
        payload,
        columns=["name", "type_p", "sub_type", "bear_bull", "end_date", "hist_win_w20"],
        headers=["TICKER", "TYPE", "SUBTYPE", "DIR", "END", "WIN20"],
        table=table,
        transform=lambda r: {**r, "name": r.get("name") or r.get("ticker")},
    )


# -- ticker -------------------------------------------------------------------
@cli.command()
@click.argument("symbol")
@click.option("--table", is_flag=True, help="Human-readable instead of JSON.")
@click.pass_context
def ticker(ctx, symbol: str, table: bool):
    """Current MA200 deviation + recent patterns for a single SYMBOL."""
    info = _client(ctx.obj["api_key"]).ticker(symbol)
    if not table:
        click.echo(fmt.as_json(info))
        return
    dev = info.get("deviation")
    click.echo(f"{info.get('ticker')}  ({'paid' if info.get('is_billed') else 'free'} tier)")
    if dev:
        click.echo(
            f"  deviation: {fmt.pct(dev.get('deviation'))}  "
            f"(close {dev.get('close')}, MA200 {dev.get('ma200')}, "
            f"as of {dev.get('snapshot_date')})"
        )
    else:
        click.echo("  deviation: not in latest snapshot")
    click.echo("  patterns:")
    pats = info.get("patterns") or []
    if not pats:
        click.echo("    (none)")
    else:
        click.echo(
            fmt.table(
                pats,
                ["type_p", "sub_type", "bear_bull", "end_date", "hist_win_w20"],
                ["TYPE", "SUBTYPE", "DIR", "END", "WIN20"],
            )
        )


def main() -> None:
    try:
        cli(obj={})
    except PatternVistaError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
