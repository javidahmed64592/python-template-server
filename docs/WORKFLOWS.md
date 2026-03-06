<!-- omit from toc -->
# GitHub Workflows

Refer to the `template-python` workflow documentation for information about the CI and build workflows: https://github.com/javidahmed64592/template-python/blob/main/docs/WORKFLOWS.md

This document details the Docker-specific workflow and reusable actions to build and release the application.
They run automated checks to ensure the Docker image builds correctly and can be released reliably.

<!-- omit from toc -->
## Table of Contents
- [Reusable Actions (`./github/actions`)](#reusable-actions-githubactions)
  - [Docker Actions (`docker/**/action.yml`)](#docker-actions-dockeractionyml)
- [Workflows (`./github/workflows`)](#workflows-githubworkflows)
  - [Docker Workflow (`docker.yml`)](#docker-workflow-dockeryml)


## Reusable Actions (`./github/actions`)

The following actions can be referenced from other repositories using `javidahmed64592/python-template-server/.github/actions/{category}/{action}@main`.

### Docker Actions (`docker/**/action.yml`)

The following actions encapsulate the steps in the Docker workflow and can be referenced locally with `uses: ./.github/actions/docker/<action>`.

**build-start-services:**
- Description: Creates `.env` file from `.env.example` and starts Docker Compose services.
- Location: `build-start-services/action.yml`
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

**show-logs:**
- Description: Shows logs from a Docker Compose container.
- Location: `show-logs/action.yml`
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

**check-containers:**
- Description: Health checks the server by polling the `/api/health` endpoint.
- Location: `check-containers/action.yml`
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

**stop-services:**
- Description: Stops Docker Compose services and removes volumes and orphans.
- Location: `stop-services/action.yml`

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/stop-services
```

---

**prepare-release:**
- Description: Gets the package version, creates a release directory with essential files, builds a tarball, and uploads it as a workflow artifact.
- Location: `prepare-release/action.yml`
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
    with:
      package-name: my_package
```

---

**check-repo-name:**
- Description: Compares the repository name against the package name in `pyproject.toml` to prevent template-derived repositories from accidentally publishing releases.
- Location: `check-repo-name/action.yml`
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

**get-version:**
- Description: Extracts the version and tag from `pyproject.toml`.
- Location: `get-version/action.yml`
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

**check-tag:**
- Description: Checks if a Git tag already exists for the given version to avoid duplicate releases.
- Location: `check-tag/action.yml`
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

**generate-release-notes:**
- Description: Generates a `release_notes.md` file by substituting placeholders in `docs/RELEASE-NOTES.md`.
- Location: `generate-release-notes/action.yml`
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

## Workflows (`./github/workflows`)

### Docker Workflow (`docker.yml`)

The Docker workflow runs on pushes and pull requests to the `main` branch, and manual dispatch.
It consists of 3 jobs to build, verify, and publish the Docker image.

**Jobs:**
- `build-docker` - Builds the Docker image and verifies the server is healthy
- `prepare-release` - Packages the release tarball and uploads as artifact (depends on `build-docker`)
- `publish-release` - Publishes the Docker image to GitHub Container Registry and creates a GitHub release (depends on `prepare-release`, push to `main` only)
