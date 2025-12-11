# Multi-stage Dockerfile for Python Template Server
# Stage 1: Build stage - build wheel using uv
FROM python:3.13-slim AS builder

WORKDIR /build

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY python_template_server/ ./python_template_server/
COPY configuration ./configuration/
COPY pyproject.toml .here LICENSE README.md ./

# Build the wheel
RUN uv build --wheel

# Stage 2: Runtime stage
FROM python:3.13-slim

# Build arguments for environment-specific config
ARG ENV=dev
ARG PORT=443

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 template_server_user && \
    chown -R template_server_user:template_server_user /app

# Install uv in runtime stage
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the built wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install the wheel
RUN uv pip install --system --no-cache /tmp/*.whl && \
    rm /tmp/*.whl

# Create configuration directory
RUN mkdir -p /app/configuration && \
    chown template_server_user:template_server_user /app/configuration

# Copy included files from installed wheel
RUN SITE_PACKAGES_DIR=$(find /usr/local/lib -name "site-packages" -type d | head -1) && \
    cp "${SITE_PACKAGES_DIR}/.here" /app/.here && \
    cp "${SITE_PACKAGES_DIR}/configuration/config.json" /app/configuration/config.json && \
    cp "${SITE_PACKAGES_DIR}/LICENSE" /app/LICENSE && \
    cp "${SITE_PACKAGES_DIR}/README.md" /app/README.md

# Create startup script
RUN echo '#!/bin/sh\n\
    if [ ! -f .env ]; then\n\
    echo "Generating new token..."\n\
    generate-new-token\n\
    export $(grep -v "^#" .env | xargs)\n\
    fi\n\
    if [ ! -f certs/cert.pem ] || [ ! -f certs/key.pem ]; then\n\
    echo "Generating self-signed certificates..."\n\
    generate-certificate\n\
    fi\n\
    exec python-template-server' > /app/start.sh && \
    chmod +x /app/start.sh && \
    chown template_server_user:template_server_user /app/start.sh

# Switch to non-root user
USER template_server_user

# Expose HTTPS port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('https://localhost:$PORT/api/health', context=__import__('ssl')._create_unverified_context()).read()" || exit 1

CMD ["/app/start.sh"]
