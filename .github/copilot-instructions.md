# Python Template Server - AI Agent Instructions

## Project Overview

FastAPI-based template server providing reusable infrastructure for building secure HTTP applications.
Implements authentication, rate limiting, security headers, and observability foundations via a base `TemplateServer` class.
Developers extend `TemplateServer` to create application-specific servers (see `ExampleServer` in `main.py`).

## Architecture & Key Components

### Application Factory Pattern

- Entry: `main.py:run()` → instantiates `ExampleServer` (subclass of `TemplateServer`) → calls `.run()`
- `TemplateServer.__init__()` sets up middleware, rate limiting, and calls `setup_routes()`
- **Critical**: Middleware order matters - request logging → nginx proxy redirect → security headers → CORS → rate limiting
- **Extensibility**: Subclasses implement `setup_routes()` to add custom endpoints and `validate_config()` for config validation

### Configuration System

- `config.json` loaded via `TemplateServer.load_config()` method
- Validated using Pydantic models in `models.py` (TemplateServerConfig hierarchy)
- Subclasses override `validate_config()` to provide custom config models
- Logging configured automatically on `logging_setup.py` import with rotating file handler
- Environment variables stored in `.env` (HOST, PORT)
- CORS configuration: Enable cross-origin requests via `config.cors` settings
- Static files: Served from `static/` directory using FastAPI's `StaticFiles` mounting with custom 404 handler

### CORS Middleware

- Optional cross-origin resource sharing support via FastAPI's `CORSMiddleware`
- Controlled by `config.cors.enabled` flag (disabled by default)
- Configurable origins, methods, headers, credentials, and preflight cache duration
- When enabled, logs configuration details (origins, credentials, methods, headers)
- Typical use: Allow frontend applications on different domains to access the API

### Nginx Proxy Redirect Middleware

- Optional middleware to redirect direct access to the nginx-proxied URL
- Controlled by `config.nginx_proxy_redirect.enabled` flag (disabled by default)
- Checks for `X-Forwarded-Proto` header (set by nginx) - if missing, request is direct
- Redirects to `https://{app_name}{domain}{path}?{query}` where nginx handles authentication
- Use case: Force all access through nginx reverse proxy
- Configuration: `app_name` (subdomain like "template-server") + `domain` (like ".lab.home.arpa")
- Example: Direct access to `http://192.168.1.100:8000/dashboard` redirects to `https://template-server.lab.home.arpa/dashboard`, nginx then handles auth flow

### Rate Limiting

- Uses `slowapi` with configurable storage (in-memory/Redis/Memcached)
- Applied via `_limit_route()` wrapper when `config.rate_limit.enabled=true`
- Custom exception handler increments `rate_limit_exceeded_counter` per endpoint
- Format: `"100/minute"` (supports /second, /minute, /hour)

### Static File Serving

- Serves static files from `static/` directory using FastAPI's `StaticFiles` class (configurable via `STATIC_DIR` constant)
- Automatically mounts `StaticFiles` at root (`/`) when `static_dir_exists=True` with `html=True` parameter
- **Nginx Error Handling**: When behind nginx reverse proxy with `proxy_intercept_errors on`, nginx handles 404s by redirecting to auth server's error page
- **No Authentication**: Static files served without API key verification (authentication handled by nginx auth_request)
- **No Rate Limiting**: Static file mounting excludes rate limiting for performance
- **Implementation**: `app.mount("/", StaticFiles(directory=str(self.static_dir), html=True), name="static")`
- Use case: Serve Single Page Applications (SPAs) alongside the API

### Observability Stack

- **Logging**: Dual output (console + rotating file), 10MB per file, 5 backups in `logs/`
- **Request Tracking**: `RequestLoggingMiddleware` logs all requests with client IP

## Developer Workflows

### Essential Commands

```powershell
# Setup (first time)
uv sync                          # Install dependencies

# Development
uv run python-template-server    # Start server (http://localhost:8000/api)
uv run -m pytest                 # Run tests with coverage
uv run -m ty check .             # Type checking
uv run -m ruff check .           # Linting

# Docker Development
docker compose up --build -d     # Build + start all services
docker compose logs -f python-template-server  # View logs
docker compose down              # Stop and remove containers
```

### Testing Patterns

- **Fixtures**: All tests use `conftest.py` fixtures, auto-mock `pyhere.here()` to tmp_path
- **Config Mocking**: Use fixtures for consistent test config
- **Integration Tests**: Test via FastAPI TestClient with auth headers
- **Coverage Target**: 99% (currently achieved)
- **Pattern**: Unit tests per module (test\_\*.py) + integration tests (test_template_server.py)

### Docker Multi-Stage Build

- **Stage 1 (backend-builder)**: Uses `uv` to build wheel with pyproject.toml, source code, and metadata files
- **Stage 2 (runtime)**: Installs wheel, copies configuration from host, copies static files and `.here` from installed package to /app
- **Config Selection**: Uses `config.json` copied from host configuration directory
- **Environment Variables**: `HOST` (default: 0.0.0.0), `PORT` (default: 8000)
- **Health Check**: Python urllib request to `/api/health` with unverified SSL context (no auth required)
- **Note**: No user switching - runs as root (could be security improvement)

## Project-Specific Conventions

### Code Organization

- **Handlers**: Module for auth (`authentication_handler.py`)
- **Middleware**: Dedicated package `middleware/` with base classes extending `BaseHTTPMiddleware`
- **Constants**: All magic strings/numbers in `constants.py` (ports, file names, log config, static directory)
- **Models**: Pydantic models for config + API responses, use `@property` for derived values
- **Static Files**: Optional `static/` directory for serving SPAs or static assets

### Security Patterns

- **Path validation**: Use Pydantic validators
- **Security headers**: HSTS, CSP, X-Frame-Options via `SecurityHeadersMiddleware`

### API Design

- **Prefix**: All routes under `/api` (API_PREFIX constant)
- **Authentication**: Applied via `dependencies=[Security(self._verify_api_key)]` in route registration
- **Response Models**: All endpoints return `BaseResponse` subclasses with code/message/timestamp

### Logging Format

- Format: `[DD/MM/YYYY | HH:MM:SS] (LEVEL) module: message`
- Client IPs logged in requests: `"Request: GET /api/health from 192.168.1.1"`
- Auth failures: `"Invalid API key attempt!"`

## Development Constraints

### Testing Requirements

- Use fixtures for TemplateServer/ExampleServer instantiation
- Test async endpoints with `@pytest.mark.asyncio`
- Mock `uvicorn.run` when testing server `.run()` methods

### CI/CD Validation

All PRs must pass:

**CI Workflow (ci.yml):**

1. `validate-pyproject` - pyproject.toml schema validation
2. `ruff` - linting (120 char line length, strict rules in pyproject.toml)
3. `ty` - 100% type coverage (strict mode)
4. `pytest` - 99% code coverage, HTML report uploaded
5. `bandit` - security check for Python code
6. `pip-audit` - audit dependencies for known vulnerabilities
7. `version-check` - pyproject.toml vs uv.lock version consistency

**Build Workflow (build.yml):**

1. `build-wheel` - Create and upload Python wheel package
2. `verify-structure` - Verify installed package structure and required files

**Docker Workflow (docker.yml):**

1. `build` - Build and test development image with docker compose

## Quick Reference

### Key Files

- `template_server.py` - Base TemplateServer class with middleware/auth setup
- `main.py` - ExampleServer implementation showing how to extend TemplateServer
- `logging_setup.py` - Logging configuration (executed on import)
- `models.py` - All Pydantic models (config + responses)
- `constants.py` - Project constants, logging config
- `docker-compose.yml` - Container stack

### Environment Variables

- `HOST` - Server host address (default: 127.0.0.1)
- `PORT` - Server port (default: 8000)

### Configuration Files

- `configuration/config.json` - Server configuration (rate limiting, security, CORS, etc.)
- `.env.example` - Template for environment variables (HOST, PORT)
