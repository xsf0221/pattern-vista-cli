import responses

from pattern_vista.client import PatternVistaClient, PatternVistaError
from pattern_vista import constants

BASE = "https://test.supabase.co"


def _client():
    return PatternVistaClient("pv_live_testkey", base_url=BASE, anon_key="anon")


def test_missing_key_raises():
    try:
        PatternVistaClient("")
    except PatternVistaError as e:
        assert "API key" in str(e)
    else:
        raise AssertionError("expected PatternVistaError")


@responses.activate
def test_deviation_passes_params_and_returns_payload():
    responses.add(
        responses.POST,
        f"{BASE}/rest/v1/rpc/{constants.RPC_DEVIATION}",
        json={"is_billed": True, "rows": [{"ticker": "AMD", "deviation": 0.5}]},
        status=200,
    )
    out = _client().deviation("over", limit=5)
    assert out["rows"][0]["ticker"] == "AMD"
    body = responses.calls[0].request.body.decode()
    assert '"p_direction": "over"' in body
    assert '"p_api_key": "pv_live_testkey"' in body


def test_bad_direction_rejected_client_side():
    try:
        _client().deviation("sideways")
    except PatternVistaError:
        pass
    else:
        raise AssertionError("expected rejection")


@responses.activate
def test_invalid_key_maps_to_friendly_error():
    responses.add(
        responses.POST,
        f"{BASE}/rest/v1/rpc/{constants.RPC_VALIDATE}",
        json={"message": "invalid_api_key"},
        status=400,
    )
    try:
        _client().whoami()
    except PatternVistaError as e:
        assert "Invalid or revoked" in str(e)
    else:
        raise AssertionError("expected PatternVistaError")


@responses.activate
def test_whoami_unwraps_single_row():
    responses.add(
        responses.POST,
        f"{BASE}/rest/v1/rpc/{constants.RPC_VALIDATE}",
        json=[{"user_id": "u1", "email": "a@b.com", "is_billed": False}],
        status=200,
    )
    info = _client().whoami()
    assert info["email"] == "a@b.com" and info["is_billed"] is False


@responses.activate
def test_market_stretch_passes_days_and_returns_payload():
    responses.add(
        responses.POST,
        f"{BASE}/rest/v1/rpc/{constants.RPC_STRETCH}",
        json={
            "is_billed": False,
            "current": {"snapshot_date": "2026-09-04", "pct_above": 0.64, "total": 217},
            "percentile": 0.81,
            "history": [{"snapshot_date": "2026-09-03", "pct_above": 0.62}],
        },
        status=200,
    )
    out = _client().market_stretch(days=30)
    assert out["current"]["pct_above"] == 0.64
    assert out["percentile"] == 0.81
    body = responses.calls[0].request.body.decode()
    assert '"p_days": 30' in body
    assert '"p_api_key": "pv_live_testkey"' in body


@responses.activate
def test_market_stretch_free_tier_gets_the_full_series():
    """Breadth is deliberately not tier-gated: the public /market/stretch page
    gives the same reading away in full, so truncating it in the agent channel
    would only make the CLI worse than a browser. The client must therefore
    pass a free-tier payload straight through rather than trimming it."""
    history = [{"snapshot_date": f"2026-08-{d:02d}", "pct_above": 0.5} for d in range(1, 21)]
    responses.add(
        responses.POST,
        f"{BASE}/rest/v1/rpc/{constants.RPC_STRETCH}",
        json={"is_billed": False, "current": {"pct_above": 0.5}, "history": history},
        status=200,
    )
    out = _client().market_stretch(days=20)
    assert out["is_billed"] is False
    assert len(out["history"]) == 20
