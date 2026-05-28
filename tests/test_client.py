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
