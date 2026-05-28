"""Project-level constants.

The Supabase URL and anon key are PUBLIC values (they ship to every browser
that loads www.pattern-vista.com), so baking them into the client is safe — the
user's per-account secret is their api_key, never the anon key.

Both can be overridden via environment variables, which is handy for pointing
the CLI at a staging project during development.
"""

import os

# Public values — these ship to every browser that loads www.pattern-vista.com
# (NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY in the web app), so
# baking them into the wheel is safe. Per-account secrets are the user's api_key.
SUPABASE_URL = os.environ.get(
    "PATTERN_VISTA_SUPABASE_URL",
    "https://agqoguhefgwxfpncrwqa.supabase.co",
)
SUPABASE_ANON_KEY = os.environ.get(
    "PATTERN_VISTA_SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFncW9ndWhlZmd3eGZwbmNyd3FhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjAxNDc3NjQsImV4cCI6MjAzNTcyMzc2NH0.lja65XlGEupLMS6tnedYCgUTXKDXzzHuEu0s9MX1ynY",
)

# Environment variable an agent/user can set instead of running `pv config set-key`.
API_KEY_ENV = "PATTERN_VISTA_API_KEY"

# RPC names (must match migrations/sql/20260527_api_keys_cli.sql in QuantToys).
RPC_VALIDATE = "cli_validate_key"
RPC_DEVIATION = "cli_get_deviation_rankings"
RPC_PATTERNS = "cli_get_recommended_patterns"
RPC_TICKER = "cli_get_ticker"

DEFAULT_TIMEOUT = 15  # seconds
