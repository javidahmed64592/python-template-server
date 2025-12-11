# GitHub Workflows

This document details the CI/CD workflows to build and release the Python Template Server application.
They run automated code quality checks to ensure code remains robust, maintainable, and testable.

## CI Workflow

The CI workflow runs on pushes and pull requests to the `main` branch.
It consists of the following jobs:

### validate-pyproject
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Validate `pyproject.toml` structure using `validate-pyproject`

### ruff
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Run Ruff linter with `uv run -m ruff check`

### mypy
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Run mypy type checking with `uv run -m mypy .`

### test
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Run pytest with coverage (HTML and terminal reports) using `uv run -m pytest --cov-report html --cov-report term`
- Fails if coverage drops below 80% (configured in `pyproject.toml`)
- Upload HTML coverage report as artifact

### bandit
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Run security scanning with bandit on `example/` directory
- Generate JSON report for artifacts
- Fail if security vulnerabilities are found

### pip-audit
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Audit dependencies for known CVEs using `pip-audit --desc`

### version-check
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Check version consistency across `pyproject.toml` and `uv.lock`

## Docker Workflow

The Docker workflow runs on pushes and pull requests to the `main` branch.
It consists of the following jobs:

### docker-development
- Checkout code
- Install uv with caching and set up Python from `.python-version`
- Create directories with proper permissions
- Build and start services with docker compose
- Show server logs
- **Health check** using reusable composite action `.github/actions/docker-check-containers` that checks Python Template Server, Prometheus, and Grafana
- Stop services

### docker-production
- Checkout code
- Install uv with caching and set up Python from `.python-version`
- Create directories with proper permissions
- Build production image with `ENV=prod` and `PORT=443` build arguments
- Start services with docker compose using production environment variables
- Show server logs
- **Health check** using reusable composite action `.github/actions/docker-check-containers` that checks Python Template Server, Prometheus, and Grafana
- Stop services
