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

### build-wheel
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Build wheel with `uv build`
- Inspect wheel contents for verification
- Upload wheel artifact (`python_template_server_wheel`)

### verify-structure
- Depends on `build-wheel` job
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
- Build and start services with `docker compose up --build -d`
- Wait for services to start (5 seconds)
- Show server logs from `python-template-server` container
- **Health check** using reusable composite action `.github/actions/docker-check-containers` with port 443
- Stop services with full cleanup: `docker compose down --volumes --remove-orphans`

### prepare-release
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Extract version from `pyproject.toml` using Python's `tomllib`
- Prepare release directory: copy `docker-compose.yml` and `README.md` to `release/`, make `install_template_server.sh` executable, rename `release/` to `python_template_server_<version>`, display directory tree
- Create compressed tarball of the release directory
- Upload tarball as artifact (`python_template_server_release`)

### check-installer
- Depends on `prepare-release` job
- Checkout code
- Setup Python environment (via custom action)
- Download release tarball artifact
- Extract tarball
- Verify pre-installation contents: check for `docker-compose.yml`, `README.md`, and executable `install_template_server.sh`
- Run installer script (non-interactive, defaults to port 443)
- Verify post-installation contents: ensure installer script is removed, check for created service files (`python-template-server.service`, `start_service.sh`, `stop_service.sh`, `uninstall_python_template_server.sh`) and verify scripts are executable

### publish-release
- Depends on `build` job
- Only runs on push to `main` branch (not PRs)
- Requires `contents: write` and `packages: write` permissions
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Extract version from `pyproject.toml` using Python's `tomllib`
- Check if Git tag already exists (skip if duplicate)
- Set up Docker Buildx for multi-platform builds
- Log in to GitHub Container Registry (ghcr.io)
- Extract Docker metadata with semantic versioning tags:
  - `v1.2.3` - Exact version
  - `1.2` - Major.minor
  - `1` - Major only
  - `latest` - Latest stable release
- Build and push multi-platform Docker images:
  - Platforms: `linux/amd64`, `linux/arm64`
  - Registry: `ghcr.io/<owner>/<repo>`
  - Uses GitHub Actions cache for layer caching
- Generate release notes
- Create GitHub Release with version tag and release notes
