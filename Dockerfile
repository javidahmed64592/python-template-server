FROM python:3.12-slim

# Build arguments for environment-specific config
ARG ENV=dev
ARG PORT=443

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 template_server_user && \
    chown -R template_server_user:template_server_user /app

# Install Git for dependency resolution
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install uv in runtime stage
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
RUN uv pip install --system git+https://github.com/javidahmed64592/python-template-server.git

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
