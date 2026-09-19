# MCP WorkBoard CrunchTools Container
# Multi-stage build: compile in the Hummingbird builder, run in Hummingbird (distroless).
#
# Build:
#   podman build -t quay.io/crunchtools/mcp-workboard .
#
# Run:
#   podman run -e WORKBOARD_API_TOKEN=your_token quay.io/crunchtools/mcp-workboard
#
# With Claude Code:
#   claude mcp add mcp-workboard \
#     --env WORKBOARD_API_TOKEN=your_token \
#     -- podman run -i --rm -e WORKBOARD_API_TOKEN quay.io/crunchtools/mcp-workboard

# --- Build stage (has /bin/sh, pip, etc.) ---

# Stage 1: Builder (has a shell, dnf and build tools)
FROM quay.io/hummingbird/python:latest-builder AS builder
USER 0
WORKDIR /app
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Stage 2: Runtime (distroless -- no shell, no package manager)
FROM quay.io/hummingbird/python:latest

LABEL name="mcp-workboard-crunchtools" \
      version="0.7.0" \
      summary="Secure MCP server for WorkBoard OKR and strategy execution" \
      description="A security-focused MCP server for WorkBoard built on Red Hat UBI" \
      maintainer="crunchtools.com" \
      url="https://github.com/crunchtools/mcp-workboard" \
      io.k8s.display-name="MCP WorkBoard CrunchTools" \
      io.openshift.tags="mcp,workboard,okr" \
      org.opencontainers.image.source="https://github.com/crunchtools/mcp-workboard" \
      org.opencontainers.image.description="Secure MCP server for WorkBoard OKR and strategy execution" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later"

WORKDIR /app

COPY --from=builder /app/venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Verify the install. Exec form: this stage has no /bin/sh for RUN's shell form.
RUN ["python3", "-c", "from mcp_workboard_crunchtools import main; print('Installation verified')"]

# Default: stdio transport (use -i with podman run)
# HTTP:    --transport streamable-http (use -d -p 8000:8000 with podman run)
EXPOSE 8000
ENTRYPOINT ["python", "-m", "mcp_workboard_crunchtools"]
