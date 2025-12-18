<!-- omit from toc -->
# Software Maintenance Guide

This document outlines how to configure and setup a development environment to work on the Python Template Server application.

<!-- omit from toc -->
## Table of Contents
- [Backend (Python)](#backend-python)
  - [Directory Structure](#directory-structure)
  - [Architecture Overview](#architecture-overview)
  - [Installing Dependencies](#installing-dependencies)
  - [Setting Up Certificates and Authentication](#setting-up-certificates-and-authentication)
    - [Generating SSL Certificates](#generating-ssl-certificates)
    - [Generating API Authentication Tokens](#generating-api-authentication-tokens)
  - [Running the Backend](#running-the-backend)
  - [Testing, Linting, and Type Checking](#testing-linting-and-type-checking)

## Backend (Python)

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=ffd343)](https://docs.python.org/3.13/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json&style=flat-square)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square)](https://github.com/astral-sh/ruff)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

### Directory Structure

```
python_template_server/
├── middleware/
│   ├── request_logging_middleware.py  # Request logging
│   └── security_headers_middleware.py # Security headers
├── authentication_handler.py          # Authentication (token generation/verification)
├── certificate_handler.py             # SSL certificate generator
├── constants.py                       # Server constants
├── logging_setup.py                   # Logging configuration
├── main.py                            # Application entry point with ExampleServer
├── models.py                          # Pydantic models (config + API responses)
├── prometheus_handler.py              # Prometheus metrics handler
└── template_server.py                 # TemplateServer base class (reusable foundation)
```

### Architecture Overview

The Python Template Server uses a **`TemplateServer` base class** that provides reusable infrastructure for building FastAPI applications:

**TemplateServer Responsibilities:**
- **Middleware Setup**: Request logging and security headers
- **Authentication**: API key verification with SHA-256 hashing
- **Rate Limiting**: Configurable request throttling per endpoint
- **Metrics**: Prometheus instrumentation for observability
- **Configuration**: JSON-based config loading and validation

**Application-Specific Servers** (like `ExampleServer` in `main.py`) extend `TemplateServer` to:
- Define custom API endpoints via `setup_routes()`
- Implement domain-specific business logic
- Validate custom configuration models via `validate_config()`

This separation ensures that cross-cutting concerns (security, logging, metrics) are handled by the base class, while application developers focus on building their API functionality.

### Installing Dependencies

This repository is managed using the `uv` Python project manager: https://docs.astral.sh/uv/

To install `uv`:

```sh
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" # Windows
```

Install the required dependencies:

```sh
uv sync
```

To include development dependencies:

```sh
uv sync --extra dev
```

After installing dev dependencies, set up pre-commit hooks:

```sh
    uv run pre-commit install
```

### Setting Up Certificates and Authentication

Before running the server, you need to generate SSL certificates and an API authentication token.

#### Generating SSL Certificates

The server requires self-signed SSL certificates for HTTPS support:

```sh
uv run generate-certificate
```

This command:
- Creates a self-signed certificate valid for 365 days
- Generates RSA-4096 key pairs
- Saves certificates to the `certs/` directory (`cert.pem` and `key.pem`)

#### Generating API Authentication Tokens

Generate a secure API token for authenticating requests:

```sh
uv run generate-new-token
```

This command:
- Creates a cryptographically secure token using Python's `secrets` module
- Hashes the token with SHA-256 for safe storage
- Stores the hash in `.env` file
- Displays the plain token (save it securely - it won't be shown again)

### Running the Backend

Start the FastAPI server:

```sh
uv run python-template-server
```

The backend will be available at `https://localhost:443/api` by default.

**Available Endpoints:**
- Prometheus Metrics: `https://localhost:443/api/metrics`
- Health Check: `https://localhost:443/api/health`
- Login: `https://localhost:443/api/login` (requires authentication)

**Testing the API:**
```sh
# Health check (no auth required)
curl -k https://localhost:443/api/health

# Metrics endpoint (no auth required)
curl -k https://localhost:443/api/metrics

# Login endpoint (requires authentication)
curl -k -H "X-API-Key: your-token-here" https://localhost:443/api/login
```

### Testing, Linting, and Type Checking

- **Run all pre-commit checks:** `uv run pre-commit run --all-files`
- **Lint code:** `uv run ruff check .`
- **Format code:** `uv run ruff format .`
- **Type check:** `uv run mypy .`
- **Run tests:** `uv run pytest`
- **Security scan:** `uv run bandit -r example/`
- **Audit dependencies:** `uv run pip-audit`
