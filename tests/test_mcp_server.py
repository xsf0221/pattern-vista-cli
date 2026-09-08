"""The MCP server is a thin re-export of the client, so these tests check the
wiring an agent actually depends on: that every tool is registered, carries a
description, and declares the arguments the client method needs.

Skipped entirely when the `mcp` extra is not installed — it is optional, and a
CLI-only install must still have a green suite.
"""

import pytest

pytest.importorskip("mcp", reason="the [mcp] extra is not installed")

import asyncio

from pattern_vista import mcp_server


EXPECTED = {
    "market_stretch",
    "deviation_ranking",
    "recommended_patterns",
    "ticker_report",
    "account_status",
}


def _tools():
    return asyncio.run(mcp_server.mcp.list_tools())


def _schema(tool):
    # mcp 1.x names it inputSchema, 2.x input_schema.
    return getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None) or {}


def test_every_tool_is_registered():
    assert {t.name for t in _tools()} == EXPECTED


def test_every_tool_has_a_description():
    # An agent picks a tool by its description; an undocumented one is dead
    # weight in the context window.
    for t in _tools():
        assert t.description and len(t.description.strip()) > 80, t.name


def test_schemas_declare_the_arguments():
    by_name = {t.name: _schema(t) for t in _tools()}
    assert set(by_name["deviation_ranking"]["properties"]) == {"direction", "limit"}
    assert set(by_name["market_stretch"]["properties"]) == {"days"}
    assert by_name["ticker_report"]["required"] == ["symbol"]
    assert by_name["account_status"].get("properties", {}) == {}


def test_bad_direction_is_rejected_before_any_network_call():
    with pytest.raises(Exception) as e:
        mcp_server.deviation_ranking(direction="sideways")
    assert "over" in str(e.value)
