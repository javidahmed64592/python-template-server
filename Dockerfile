# Multi-stage Dockerfile for Python Template Server
# Stage 1: Build stage - build wheel using uv
FROM python:3.13-slim AS backend-builder

WORKDIR /build

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy backend source files
COPY python_template_server/ ./python_template_server/
COPY configuration/ ./configuration/
COPY grafana/ ./grafana/
COPY prometheus/ ./prometheus/
COPY pyproject.toml .here LICENSE README.md ./

# Build the wheel
RUN uv build --wheel

# Stage 3: Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Install uv in runtime stage
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the built wheel from backend builder
COPY --from=backend-builder /build/dist/*.whl /tmp/

# Install the wheel
RUN uv pip install --system --no-cache /tmp/*.whl && \
    rm /tmp/*.whl

# Create required directories
RUN mkdir -p /app/logs /app/certs

# Copy included files from installed wheel to app directory
RUN SITE_PACKAGES_DIR=$(find /usr/local/lib -name "site-packages" -type d | head -1) && \
    cp -r "${SITE_PACKAGES_DIR}/configuration" /app/ && \
    cp -r "${SITE_PACKAGES_DIR}/grafana" /app/ && \
    cp -r "${SITE_PACKAGES_DIR}/prometheus" /app/ && \
    cp "${SITE_PACKAGES_DIR}/.here" /app/.here && \
    cp "${SITE_PACKAGES_DIR}/LICENSE" /app/LICENSE && \
    cp "${SITE_PACKAGES_DIR}/README.md" /app/README.md

# Create startup script with Ollama model checking
RUN echo '#!/bin/sh\n\
    set -e\n\
    \n\
    # Copy monitoring configs to shared volume if they do not exist\n\
    if [ -d "/monitoring-configs" ]; then\n\
    echo "Setting up monitoring configurations..."\n\
    mkdir -p /monitoring-configs/prometheus /monitoring-configs/grafana\n\
    cp -r /app/prometheus/* /monitoring-configs/prometheus/ 2>/dev/null || true\n\
    cp -r /app/grafana/* /monitoring-configs/grafana/ 2>/dev/null || true\n\
    echo "Monitoring configurations ready"\n\
    fi\n\
    \n\
    # Generate API token if needed\n\
    if [ -z "$API_TOKEN_HASH" ]; then\n\
    echo "Generating new token..."\n\
    generate-new-token\n\
    export $(grep -v "^#" .env | xargs)\n\
    fi\n\
    \n\
    # Generate certificates if needed\n\
    if [ ! -f certs/cert.pem ] || [ ! -f certs/key.pem ]; then\n\
    echo "Generating self-signed certificates..."\n\
    generate-certificate\n\
    fi\n\
    \n\
    exec python-template-server' > /app/start.sh && \
    chmod +x /app/start.sh

# Expose HTTPS port
EXPOSE 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('https://localhost:443/api/health', context=__import__('ssl')._create_unverified_context()).read()" || exit 1

CMD ["/app/start.sh"]
