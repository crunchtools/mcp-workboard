# MCP WorkBoard CrunchTools Container
# Built on Hummingbird Python image (Red Hat UBI-based) for enterprise security
#
# Build:
#   podman build -t quay.io/crunchtools/mcp-workboard .
#
# Run:
#   podman run -e WORKBOARD_API_TOKEN=your_token quay.io/crunchtools/mcp-workboard
#
# With Claude Code:
#   claude mcp add mcp-workboard-crunchtools \
#     --env WORKBOARD_API_TOKEN=your_token \
#     -- podman run -i --rm -e WORKBOARD_API_TOKEN quay.io/crunchtools/mcp-workboard

# Use Hummingbird Python image (Red Hat UBI-based with Python pre-installed)
FROM quay.io/hummingbird/python:latest

# Labels for container metadata
LABEL name="mcp-workboard-crunchtools" \
      version="0.1.0" \
      summary="Secure MCP server for WorkBoard OKR and strategy execution" \
      description="A security-focused MCP server for WorkBoard built on Red Hat UBI" \
      maintainer="crunchtools.com" \
      url="https://github.com/crunchtools/mcp-workboard" \
      io.k8s.display-name="MCP WorkBoard CrunchTools" \
      io.openshift.tags="mcp,workboard,okr"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package and dependencies
RUN pip install --no-cache-dir .

# Verify installation
RUN python -c "from mcp_workboard_crunchtools import main; print('Installation verified')"

# Default: stdio transport (use -i with podman run)
# HTTP:    --transport streamable-http (use -d -p 8000:8000 with podman run)
EXPOSE 8000
ENTRYPOINT ["python", "-m", "mcp_workboard_crunchtools"]
