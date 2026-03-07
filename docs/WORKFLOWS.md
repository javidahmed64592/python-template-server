<!-- omit from toc -->
# GitHub Workflows

This document describes all GitHub workflows and reusable actions for the Python Template Server project.

The repository includes CI and Build workflows that reference actions from the `template-python` repository.
For detailed information about these shared actions, refer to: https://github.com/javidahmed64592/template-python/blob/main/docs/WORKFLOWS.md

This document focuses on the Docker-specific workflow and reusable actions unique to this project, which handle building and releasing the containerized application.

<!-- omit from toc -->
## Table of Contents
- [Reusable Actions (`./github/actions`)](#reusable-actions-githubactions)
  - [Setup Actions (`/setup/**/action.yml`)](#setup-actions-setupactionyml)
  - [Docker Actions (`docker/**/action.yml`)](#docker-actions-dockeractionyml)
- [Workflows (`./github/workflows`)](#workflows-githubworkflows)
  - [Docker Workflow (`docker.yml`)](#docker-workflow-dockeryml)

## Reusable Actions (`./github/actions`)

The following actions can be referenced from other repositories using `javidahmed64592/python-template-server/.github/actions/{category}/{action}@main`.

### Setup Actions (`/setup/**/action.yml`)

**setup-node:**
- Description: Set up Node.js with npm cache and install dependencies.
- Location: `setup-node/action.yml`
- Steps:
  - Installs Node using `actions/setup-node@v4` with caching enabled
  - Install npm packages
- Note: Requires a frontend directory named `<repository name>-frontend`

Usage:
```yaml
steps:
  - uses: javidahmed64592/python-template-server/.github/actions/setup/setup-node@main
```

### Docker Actions (`docker/**/action.yml`)

The following actions encapsulate the steps in the Docker workflow and can be referenced locally with `uses: ./.github/actions/docker/<action>`.

**build-start-services:**
- Description: Creates `.env` file from `.env.example` and starts Docker Compose services.
- Location: `build-start-services/action.yml`
- Steps:
  - Moves `.env.example` to `.env`
  - Runs `docker compose [build-args] up --build -d`
  - Sleeps for `wait-seconds`

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/build-start-services
    with:
      wait-seconds: "5"
      build-args: ""
```

---

**show-logs:**
- Description: Shows logs from a Docker Compose container.
- Location: `show-logs/action.yml`
- Steps:
  - Displays logs using `docker compose logs` for the repository name

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/show-logs
```

---

**check-containers:**
- Description: Health checks the server by polling the `/api/health` endpoint.
- Location: `check-containers/action.yml`

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/check-containers
    with:
      port: 443
      num-retries: "5"
      timeout-seconds: "5"
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
- Outputs:
  - `package-dir` - Release directory name (e.g. `python_template_server_1.2.3`)
- Steps:
  - Extracts version via `uv run ci-pyproject-version`
  - Creates release directory and copies `docker-compose.yml`, `README.md`, `LICENSE`, `.env.example`
  - Creates compressed tarball
  - Uploads tarball as artifact named `{PACKAGE_NAME}_release`
- Note: Requires `PACKAGE_NAME` environment variable to be set

Usage:
```yaml
steps:
  - uses: javidahmed64592/template-python/.github/actions/setup/install-python-dev@main
  - uses: ./.github/actions/docker/prepare-release
```

---

**check-repo-name:**
- Description: Compares the repository name against the package name in `pyproject.toml` to prevent template-derived repositories from accidentally publishing releases.
- Location: `check-repo-name/action.yml`
- Outputs:
  - `should_release` - `"true"` if names match, `"false"` otherwise
- Steps:
  - Extracts package name via `uv run ci-pyproject-name`
  - Compares repository name with package name
  - Sets output based on match result

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/check-repo-name
    id: check_repo_name
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
- Outputs:
  - `release_notes_file` - Path to the generated file (`release_notes.md`)
- Steps:
  - Substitutes `{{VERSION}}`, `{{CONTAINER_NAME}}`, `{{PACKAGE_NAME}}`, and `{{REPOSITORY}}` placeholders
  - Container name and repository are derived from GitHub context
  - Package name is taken from `PACKAGE_NAME` environment variable

Usage:
```yaml
steps:
  - uses: ./.github/actions/docker/generate-release-notes
    id: release_notes
    with:
      version: ${{ steps.get_version.outputs.version }}
```

## Workflows (`./github/workflows`)

### Docker Workflow (`docker.yml`)

The Docker workflow runs on pushes and pull requests to the `main` branch, and supports manual dispatch.
It consists of 3 jobs to build, verify, and publish the Docker image.

**Jobs:**
- `build-docker` - Builds the Docker image and verifies the server is healthy
- `prepare-release` - Packages the release tarball and uploads as artifact (depends on `build-docker`)
- `publish-release` - Publishes the Docker image to GitHub Container Registry and creates a GitHub release (depends on `prepare-release`, push to `main` only)
