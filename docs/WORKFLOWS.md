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
  - [CI Actions (`/ci/**/action.yml`)](#ci-actions-ciactionyml)
  - [Build Actions (`/build/**/action.yml`)](#build-actions-buildactionyml)
  - [Docker Actions (`docker/**/action.yml`)](#docker-actions-dockeractionyml)
- [Workflows (`./github/workflows`)](#workflows-githubworkflows)
  - [CI Workflow (`ci.yml`)](#ci-workflow-ciyml)
  - [Build Workflow (`build.yml`)](#build-workflow-buildyml)
  - [Docker Workflow (`docker.yml`)](#docker-workflow-dockeryml)

## Reusable Actions (`./github/actions`)

The following actions can be referenced from other repositories using `javidahmed64592/python-template-server/.github/actions/{category}/{action}@main`.

### Setup Actions (`/setup/**/action.yml`)

**check-frontend-exists:**
- Description: Check if the frontend directory exists in the repository to conditionally execute frontend CI and build jobs.
- Location: `check-frontend-exists/action.yml`
- Outputs:
  - `exists` - `"true"` if frontend directory exists, `"false"` otherwise
- Steps:
  - Checks for directory named `<repository name>-frontend`
  - Sets output to `true` or `false` based on directory existence
  - Logs message if directory doesn't exist
- Note: Used by CI and Build workflows to skip frontend jobs when no frontend directory is present

Usage:
```yaml
steps:
  - uses: javidahmed64592/python-template-server/.github/actions/setup/check-frontend-exists@main
    id: check-frontend
```

---

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

### CI Actions (`/ci/**/action.yml`)

**frontend:**
- Description: Runs frontend validation checks (type-checking, linting, formatting, testing) and uploads coverage reports.
- Location: `frontend/action.yml`
- Steps:
  - Uses the `setup-node` action
  - Runs `npm run type-check` for type checking
  - Runs `npm run lint` for static code analysis
  - Runs `npm run format` to tidy up scripts
  - Runs `npm run test:coverage` for frontend unit tests
  - Uploads unit test coverage report using `actions/upload-artifact@v7`

Usage:
```yaml
steps:
  - uses: javidahmed64592/python-template-server/.github/actions/ci/frontend@main
```

### Build Actions (`/build/**/action.yml`)

**build-frontend:**
- Description: Build the frontend and upload the build artifacts for use in other jobs.
- Location: `build-frontend/action.yml`
- Steps:
  - Uses the `setup-node` action
  - Runs `npm run build` to build frontend static files
  - Uploads static files as build artifact using `actions/upload-artifact@v7`

Usage:
```yaml
steps:
  - uses: javidahmed64592/python-template-server/.github/actions/build/build-frontend@main
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
- Description: Substitutes placeholders in `RELEASE-NOTES.md` with actual values.
- Location: `generate-release-notes/action.yml`
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

### CI Workflow (`ci.yml`)

The CI workflow runs on pushes and pull requests to the `main` branch.
It inherits all Python validation jobs from `template-python` and adds frontend-specific validation.

**Additional Jobs:**
- `frontend` - Conditionally executes validation checks on frontend if frontend directory exists
  - Uses `check-frontend-exists` to detect frontend directory
  - Runs `frontend` action only when frontend is present

### Build Workflow (`build.yml`)

The Build workflow runs on pushes and pull requests to the `main` branch.
It extends the base `template-python` build process with optional frontend building.

**Additional Jobs:**
- `build-frontend` - Conditionally builds frontend and outputs existence flag
  - Uses `check-frontend-exists` to detect frontend directory
  - Builds frontend static files using `build-frontend` action if present
  - Outputs `frontend-exists` flag for downstream jobs
  - Uploads frontend build artifacts

**Modified Jobs:**
- `build-wheel` - Enhanced to include frontend builds
  - Depends on `build-frontend` job
  - Downloads frontend build artifacts to `static/` directory if `frontend-exists` is `true`
  - Proceeds with standard wheel building from `template-python`

### Docker Workflow (`docker.yml`)

The Docker workflow runs on pushes and pull requests to the `main` branch, and supports manual dispatch.
It consists of 3 jobs to build, verify, and publish the Docker image.

**Jobs:**
- `build-docker` - Builds the Docker image and verifies the server is healthy
- `prepare-release` - Packages the release tarball and uploads as artifact (depends on `build-docker`)
- `publish-release` - Publishes the Docker image to GitHub Container Registry and creates a GitHub release (depends on `prepare-release`, push to `main` only)
