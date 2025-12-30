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

### pytest
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Run pytest with coverage (HTML and terminal reports) using `uv run -m pytest --cov-report html --cov-report term`
- Fails if coverage drops below 80% (configured in `pyproject.toml`)
- Upload HTML coverage report as artifact

### bandit
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Run security scanning with bandit on `python_template_server/` directory
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

## Build Workflow

The Build workflow runs on pushes and pull requests to the `main` branch.
It consists of the following jobs:

### build_wheel
  - Checkout code
  - Setup Python environment with dev dependencies (via custom action)
  - Build wheel with `uv build`
  - Inspect wheel contents for verification
  - Upload wheel artifact (`python_template_server_wheel`)

### verify_structure
  - Depends on `build_wheel` job
  - Checkout code
  - Setup Python environment (via custom action)
  - Download wheel artifact
  - Install wheel using `uv pip install`
  - Verify installed package structure in site-packages
  - Display directory structure with tree views for verification

## Docker Workflow

The Docker workflow runs on pushes, pull requests to the `main` branch, and manual dispatch.
It consists of the following jobs:

### build
  - Checkout code
  - Setup Python environment with dev dependencies (via custom action)
  - Build and start services with `docker compose --build -d`
  - Wait for services to start (5 seconds)
  - Show server logs from `python-template-server` container
  - **Health check** using reusable composite action `.github/actions/docker-check-containers`:
  - Stop services with full cleanup: `docker compose down --volumes --remove-orphans`
