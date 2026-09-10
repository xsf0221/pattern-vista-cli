# Pattern Vista MCP server.
#
# stdio transport: the MCP client talks to this container over its stdin and
# stdout, so there is no port to expose and no listener to wait on. Run it as:
#
#   docker run -i --rm -e PATTERN_VISTA_API_KEY=pv_live_xxx pattern-vista-mcp
#
# The -i is not optional — without an attached stdin the server has nothing to
# read and exits immediately.

FROM python:3.12-slim

# 3.12 rather than the 3.9 floor in pyproject: that floor covers the CLI, but
# the [mcp] extra needs 3.10+, so a 3.9 base would fail to resolve.

WORKDIR /app

# Only what the build actually needs. README.md is not documentation here —
# pyproject declares it as the package readme, so the build fails without it.
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir '.[mcp]'

# The API key is per-user and never baked in; pass it at run time. Without one
# the server still starts and every tool returns an actionable error, which is
# what lets a registry probe the tool list without credentials.
ENV PATTERN_VISTA_API_KEY=""

# Drop root: this process only reads its own config and speaks HTTPS out.
RUN useradd --create-home --uid 10001 app
USER app

ENTRYPOINT ["pattern-vista-mcp"]
