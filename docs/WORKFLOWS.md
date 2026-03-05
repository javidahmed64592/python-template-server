# GitHub Workflows

Refer to the `template-python` workflow documentation for information about the CI and build workflows: https://github.com/javidahmed64592/template-python/blob/main/docs/WORKFLOWS.md

## Docker Workflow

The Docker workflow runs on pushes, pull requests to the `main` branch, and manual dispatch.
It consists of the following jobs:

### build-docker
- Checkout code
- Create `.env` file from `.env.example` template
- Build and start services with `docker compose up --build -d`
- Wait for services to start (5 seconds)
- Show server logs from container
- **Health check** using reusable composite action `.github/actions/docker-check-containers` with port 443
- Stop services with full cleanup: `docker compose down --volumes --remove-orphans`

### prepare-release
- Depends on `build-docker` job
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- Extract version from `pyproject.toml` using Python's `tomllib`
- Prepare release directory
- Display directory tree structure
- Create compressed tarball of the release directory
- Upload tarball as artifact

### publish-release
- Depends on `prepare-release` job
- Only runs on push to `main` branch (not PRs)
- Requires `contents: write` and `packages: write` permissions
- Checkout code
- Setup Python environment with core dependencies (via custom action)
- Check repository name matches package name: Compares repository name with package name in `pyproject.toml` to prevent template-derived repositories from publishing releases under the template name (all subsequent steps skipped if names don't match)
- Extract version from `pyproject.toml` using Python's `tomllib`
- Check if Git tag already exists (skip if duplicate)
- Download release tarball artifact
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
