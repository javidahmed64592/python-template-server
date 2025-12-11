[![python](https://img.shields.io/badge/Python-3.13-3776AB.svg?style=flat&logo=python&logoColor=ffd343)](https://docs.python.org/3.13/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![CI](https://img.shields.io/github/actions/workflow/status/javidahmed64592/python-template-server/ci.yml?branch=main&style=flat-square&label=CI&logo=github)](https://github.com/javidahmed64592/python-template-server/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/github/actions/workflow/status/javidahmed64592/python-template-server/docker.yml?branch=main&style=flat-square&label=Docker&logo=github)](https://github.com/javidahmed64592/python-template-server/actions/workflows/docker.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- omit from toc -->
# Python Template Server

A production-ready FastAPI server template with built-in authentication, rate limiting, security headers, and Prometheus metrics. This repository provides a solid foundation for building secure, observable FastAPI applications.

<!-- omit from toc -->
## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Generate Certificates and API Token](#generate-certificates-and-api-token)
  - [Run the Server](#run-the-server)
- [Using as a Template](#using-as-a-template)
- [Docker Deployment](#docker-deployment)
- [Documentation](#documentation)
- [License](#license)

## Features

- **TemplateServer Base Class**: Reusable foundation
- **FastAPI Framework**: Modern, fast, async-ready web framework
- **Observability Stack**: Pre-configured Prometheus + Grafana dashboards
- **Docker Support**: Multi-stage builds with docker-compose orchestration
- **Production Patterns**: Token generation, SSL certificate handling, health checks

## Architecture

This project uses a **`TemplateServer` base class** that encapsulates cross-cutting concerns:

- **Request Logging**: All requests/responses logged with client IP tracking
- **Security Headers**: HSTS/CSP/X-Frame-Options automatically applied
- **API Key Verification**: SHA-256 hashed tokens with secure validation
- **Rate Limiting**: Configurable limits using `slowapi` (in-memory/Redis/Memcached)
- **Prometheus Metrics**: Custom authentication/rate-limit metrics + HTTP instrumentation

**Application-specific servers** (like `ExampleServer` in `main.py`) extend `TemplateServer` to implement domain-specific endpoints and business logic. The base class handles all infrastructure concerns, letting you focus on your API functionality.

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

Install `uv`:

```sh
# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installation

```sh
# Clone the repository
git clone https://github.com/javidahmed64592/python-template-server.git
cd python-template-server

# Install dependencies
uv sync --extra dev
```

### Generate Certificates and API Token

```sh
# Generate self-signed SSL certificate (saves to certs/ directory)
uv run generate-certificate

# Generate API authentication token (saves hash to .env)
uv run generate-new-token
# ⚠️ Save the displayed token - you'll need it for API requests!
```

### Run the Server

```sh
# Start the server
uv run python-template-server

# Server runs at https://localhost:443/api
# Health check: curl -k https://localhost:443/api/health
# Metrics: curl -k https://localhost:443/api/metrics
```

## Using as a Template

To create your own server:

1. **Create a subclass of `TemplateServer`** (see `python_template_server/main.py:ExampleServer` as reference)
2. **Implement required methods**:
   - `validate_config()`: Validate your config model
   - `setup_routes()`: Define your API endpoints
3. **Add custom routes** using FastAPI decorators on `self.app`
4. **Configure** via `configuration/config.json`

See the [Software Maintenance Guide](./docs/SMG.md) for detailed setup instructions.

## Docker Deployment

```sh
# Start all services (FastAPI + Prometheus + Grafana)
docker compose up -d

# View logs
docker compose logs -f python-template-server

# Access services:
# - API: https://localhost:443/api
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

## Documentation

- **[API Documentation](./docs/API.md)**: Endpoints, authentication, metrics
- **[Software Maintenance Guide](./docs/SMG.md)**: Development setup, configuration
- **[Docker Deployment Guide](./docs/DOCKER_DEPLOYMENT.md)**: Container orchestration
- **[Workflows](./docs/WORKFLOWS.md)**: CI/CD pipeline details

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
