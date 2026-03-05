# GitHub Workflows

Refer to the `template-python` workflow documentation for information about the CI and build workflows: https://github.com/javidahmed64592/template-python/blob/main/docs/WORKFLOWS.md

## Docker Actions (`.github/actions/docker/**/action.yml`)

The following actions encapsulate the steps in the Docker workflow and can be
referenced locally with `uses: ./.github/actions/docker/<action>`.

### build-start-services

- Description: Creates `.env` file from `.env.example` and starts Docker Compose services.
- Location: `docker/build-start-services/action.yml`
- Inputs:
  - `wait-seconds` (default: `"5"`) - Seconds to wait after starting services
- Steps:
  - Renames `.env.example` to `.env`
  - Runs `docker compose up --build -d`
  - Sleeps for `wait-seconds`

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/build-start-services
```

---

### show-logs

- Description: Shows logs from a Docker Compose container.
- Location: `docker/show-logs/action.yml`
- Inputs:
  - `container-name` (required) - Name of the container

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/show-logs
    with:
      container-name: my-container
```

---

### check-containers

- Description: Health checks the server by polling the `/api/health` endpoint.
- Location: `docker/check-containers/action.yml`
- Inputs:
  - `port` (required) - Port to check
  - `num-retries` (default: `"5"`) - Number of retry attempts
  - `timeout-seconds` (default: `"5"`) - Seconds between retries

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/check-containers
    with:
      port: 443
```

---

### stop-services

- Description: Stops Docker Compose services and removes volumes and orphans.
- Location: `docker/stop-services/action.yml`

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/stop-services
```

---

### prepare-release

- Description: Gets the package version, creates a release directory with essential files, builds a tarball, and uploads it as a workflow artifact.
- Location: `docker/prepare-release/action.yml`
- Inputs:
  - `package-name` (required) - Python package name
- Outputs:
  - `package-dir` - Release directory name (e.g. `python_template_server_1.2.3`)
- Steps:
  - Extracts version via `uv run ci-pyproject-version`
  - Creates release directory and copies `docker-compose.yml`, `README.md`, `LICENSE`, `.env.example`
  - Creates compressed tarball
  - Uploads tarball as artifact named `{package-name}_release`

Usage:
```yaml
steps:
  - uses: javidahmed64592/template-python/.github/actions/setup/install-python-dev@main
  - uses: ./.github/actions/docker/prepare-release
    id: prepare_release
    with:
      package-name: my_package
```

---

### check-repo-name

- Description: Compares the repository name against the package name in `pyproject.toml` to prevent template-derived repositories from accidentally publishing releases.
- Location: `docker/check-repo-name/action.yml`
- Inputs:
  - `repository` (required) - Full repository name (`owner/repo`)
- Outputs:
  - `should_release` - `"true"` if names match, `"false"` otherwise

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/check-repo-name
    id: check_repo_name
    with:
      repository: ${{ github.repository }}
```

---

### get-version

- Description: Extracts the version and tag from `pyproject.toml`.
- Location: `docker/get-version/action.yml`
- Outputs:
  - `version` - Version string (e.g. `1.2.3`)
  - `tag` - Version tag (e.g. `v1.2.3`)

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/get-version
    id: get_version
```

---

### check-tag

- Description: Checks if a Git tag already exists for the given version to avoid duplicate releases.
- Location: `docker/check-tag/action.yml`
- Inputs:
  - `version` (required) - Version string without the `v` prefix
- Outputs:
  - `tag_exists` - `"true"` if the tag exists, `"false"` otherwise

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/check-tag
    id: check_tag
    with:
      version: ${{ steps.get_version.outputs.version }}
```

---

### generate-release-notes

- Description: Generates a `release_notes.md` file with quick-start instructions and links.
- Location: `docker/generate-release-notes/action.yml`
- Inputs:
  - `version` (required) - Release version (without `v` prefix)
  - `container-name` (required) - Docker container name
  - `package-name` (required) - Python package name
  - `repository` (required) - Full repository name (`owner/repo`)
- Outputs:
  - `release_notes_file` - Path to the generated file (`release_notes.md`)

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/generate-release-notes
    id: release_notes
    with:
      version: ${{ steps.get_version.outputs.version }}
      container-name: my-container
      package-name: my_package
      repository: ${{ github.repository }}
```

## Docker Workflow

The Docker workflow runs on pushes, pull requests to the `main` branch, and manual dispatch.
It consists of the following jobs:

### build-docker
- Checkout code
- **Build and start services** using `docker/build-start-services` action
- **Show server logs** using `docker/show-logs` action
- **Health check** using `docker/check-containers` action with port 443
- **Stop services** using `docker/stop-services` action

### prepare-release
- Depends on `build-docker` job
- Checkout code
- Setup Python environment with dev dependencies (via custom action)
- **Prepare and upload release tarball** using `docker/prepare-release` action

### publish-release
- Depends on `prepare-release` job
- Only runs on push to `main` branch (not PRs)
- Requires `contents: write` and `packages: write` permissions
- Checkout code
- Setup Python environment with core dependencies (via custom action)
- **Check repository name** using `docker/check-repo-name` action (all subsequent steps skipped if names don't match)
- **Get version** using `docker/get-version` action
- **Check if tag exists** using `docker/check-tag` action (skips release if duplicate)
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
- **Generate release notes** using `docker/generate-release-notes` action
- Create GitHub Release with version tag and release notes
