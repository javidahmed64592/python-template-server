# TemplateServer Extraction & Documentation Updates

This file captures suggested documentation updates and a recommended migration plan for extracting the `TemplateServer` class from this repository into a standalone, reusable Python package.

Summary
-------
- `TemplateServer` was extracted from `CloudServer` and moved to `python_cloud_server/template_server.py`.
- `CloudServer` now inherits from `TemplateServer`, which centralizes middleware, authentication verification, rate limiting and Prometheus metrics.
- The `TemplateServer` class is intended to be a reusable foundation for building FastAPI servers and will be published as a separate Python package in the future.

Purpose of this document
------------------------
- Provide a list of documentation and CI changes required to reflect the new project architecture.
- Offer exact wording snippets, file-level guidance and a migration checklist so the maintainers can implement everything once the package is published.

Recommended package name (examples)
-----------------------------------
- `python-template-server`
- `fastapi-template-server`
- `template-server` (namespace choice depends on PyPI/ownership)

If you have a specific package name you prefer, update the steps below accordingly.

Files to update (anthology)
---------------------------
Below are each of the doc files that should be updated, why an update is necessary, and an example patch or snippet you can apply.

1) README.md
- Why: README is the main entry and should document the new architecture, the `TemplateServer` concept and the migration plan.
- Suggested snippets:

Add under "Features":

> - TemplateServer (reusable base): Consolidates request logging, security headers, rate limiting, Prometheus instrumentation, and token validation into a single base class. `CloudServer` now inherits from `TemplateServer` to define cloud-storage-specific endpoints and domain logic.

Add a new "Architecture" section (after Features):

```
## Architecture

The project uses a `TemplateServer` base class that encapsulates cross-cutting concerns: request logging, security headers (HSTS/CSP), API key verification, rate limiting, and Prometheus metrics. Application-specific server classes (e.g., `CloudServer`) extend `TemplateServer` to implement domain-specific endpoints and behavior.

Optionally: the `TemplateServer` is planned to be extracted into a reusable package for publishing on PyPI or an internal registry; this repo may add it as a dependency and remove the local module in a follow-up.
```

2) docs/SMG.md (Software Maintenance Guide)
- Why: Directory listing and setup instructions should reflect the new module (and note the future package)

Add to "Directory Structure":

```
python_cloud_server/
├── template_server.py                 # Base server class (reusable). Note: may be published as separate package.
├── cloud_server.py                    # Cloud server subclass that defines cloud-specific endpoints via TemplateServer
├── authentication_handler.py          # Authentication
├── certificate_handler.py             # Certificate generator
├── config.py                          # Configuration management
├── constants.py                       # Server constants
├── main.py                            # Application entry point
└── models.py                          # Pydantic models
```

Add a short "Architecture - TemplateServer" section:

```
### Architectural Notes — TemplateServer

`TemplateServer` centralizes middleware, authentication verification, rate limiting, and Prometheus instrumentation. `CloudServer` extends this to add cloud-storage-specific routes. The `TemplateServer` class will be extracted as a reusable package in a future release; when it is, update the repo's `pyproject.toml` to include it as a dependency.
```

3) docs/API.md
- Why: API docs should clarify that most cross-cutting functionality is implemented by `TemplateServer` (so users or maintainers know where that behavior comes from)

Add a short note near the top:

```
Note: The `CloudServer` implementation inherits common behaviors (authentication, rate limiting, security headers, instrumentation) from a `TemplateServer` base class. These behaviors are applied by the base class to endpoints.
```

No endpoint behavior changes are required unless you change the public API.

4) docs/DOCKER_DEPLOYMENT.md
- Why: Docker builds may need to install the new external package; mention packaging options and Docker build considerations.

Add a short note under `Building and Running` or `Configuration`:

```
If the `TemplateServer` class is published as a separate package, ensure it is included in `pyproject.toml` and installed during `uv sync` (or `pip install`) so the Docker image contains the dependency. For local development, continue to ship the module in the repo as a development fallback until the package is published and version pinned.
```

5) docs/WORKFLOWS.md
- Why: CI should install the package if it becomes external and not part of the repo.

Add or update steps in `validate-pyproject` and `test` jobs:

```
- Ensure `pyproject.toml` lists the extracted `TemplateServer` package (if it's published and required as an external dependency); CI will install it during `uv sync --extra dev`.
```

6) Optionally update `.github/cicd` and internal docs
- Why: If publishing the package, maintainers may want to add automation to build and publish the package, or update release notes and checkers to ensure compatibility.

Add a short reference in relevant CI docs about publishing/pinning the `TemplateServer` package and the versioning policy for new releases.


Test updates
------------
- If the `TemplateServer` package is published under a PyPI name and the same code is removed locally, tests must import `TemplateServer` from the published package (e.g., `from template_server_pkg import TemplateServer`) or install it in CI.
- Keep the tests referencing `python_cloud_server.template_server` while the module remains in the repo.
- After publishing, update tests to import from the package, or add an alias import in the project root to preserve compatibility during migration.

Example update steps for tests

- While TemplateServer is still in-repo (recommended during initial migration): no test changes necessary.
- After external package release: update test imports to point to the package or update `sys.path` to include the new package location in tests.

Note: If you extract the module to a separate repo and publish the package, consider adding an integration test that installs the package in a virtualenv and runs server tests to validate parity.

CI & Docker changes
-------------------
- CI job changes (if needed):
  - Add the new package as a dependency in `pyproject.toml` lock file, or ensure CI runs `uv sync` to install it.
  - If you publish a separate package, consider pinning the package in `pyproject.toml` and using a `pip` index or internal package registry for CI installs.

- Docker build changes:
  - Ensure `pyproject.toml` includes the package, so the builder installs it during the runtime stage.
  - If you publish to an internal index or private registry, update Docker build steps to authenticate and install that package.

Example `pyproject.toml` snippet to add:

```
# Add to your dependency list (example syntax may differ depending on packaging tool)
[tool.poetry.dependencies]
python-template-server = "^0.1.0"
```

Implementation & Migration Plan
-------------------------------
This migration plan aims to keep the repo functional during the extraction and publication process.

1) Keep `TemplateServer` local until first package release
   - Rationale: Minimizes immediate refactor changes for tests and deployment.
   - Action: Keep `python_cloud_server/template_server.py` in the repo and continue using the local import in the `CloudServer` module.

2) Publish the package
   - Prepare a simple package skeleton and tests in the `template-server` repo (or the new package's repo)
   - Publish the package to PyPI (or your private registry) with a version, e.g., `0.1.0`

3) Add the package to `pyproject.toml` and updates images/CI
   - Update `pyproject.toml` to include the new package as a dependency.
   - Update Dockerfile and CI workflows if you're using a private registry or the package has specific installation needs.

4) Remove local module (optional and final step)
   - Remove `python_cloud_server/template_server.py` from the cloud server repo after a new release or a deprecation window.
   - Update tests and imports to refer to the package instead of local module.

5) Update docs & README
   - Apply the docs changes outlined in this document (snippets above).
   - Add a migration note describing the package ZIP and version.

6) Update CI & workflows to install the package in the environment
   - Ensure `uv sync` installs new package; update reusable steps that run `uv run -m pytest` accordingly.

7) Verify everything with tests
   - Run unit and integration tests locally or in the CI environment.
   - For Docker, build the image with the package installed and run the health checks.

PR checklist for implementation
------------------------------
- [ ] Add `TemplateServer` package to `pyproject.toml` (once published)
- [ ] Add `TemplateServer` architecture text to `README.md` (snippet added above)
- [ ] Add `template_server.py` note to `docs/SMG.md`
- [ ] Add short note to `docs/API.md` indicating behavior comes from `TemplateServer`
- [ ] Add a Docker note to `docs/DOCKER_DEPLOYMENT.md` if the package will be installed
- [ ] Update `docs/WORKFLOWS.md` to mention unit/CI installation
- [ ] Update unit tests to import from the final package (or add alias compatibility) after package publication
- [ ] Validate the new architecture and docs in CI & Docker builds
- [ ] Add a short example `pyproject` dependency snippet to docs (seen above)

Sample docs patches (copy-paste)
-------------------------------
1) README.md Feature bullet:

> - TemplateServer (reusable base): Consolidates request logging, security headers, rate limiting, Prometheus instrumentation, and token verification into a base class. `CloudServer` inherits from `TemplateServer` and focuses on cloud-specific endpoints.

2) README.md Architecture section:

```
## Architecture

The project uses a `TemplateServer` base class that encapsulates cross-cutting concerns: request logging, security headers (HSTS/CSP), API key verification, rate limiting, and Prometheus metrics. Application-specific servers (e.g., `CloudServer`) extend `TemplateServer` to implement domain-specific endpoints and behavior.

When `TemplateServer` is released as a separate package, this repo will add it as a dependency and use that package instead of the local module.
```

3) docs/SMG.md Directory Structure addition:

```
python_cloud_server/
├── template_server.py                 # Base server class (reusable) - may be published separately
├── cloud_server.py                    # Cloud server subclass that extends TemplateServer
```

4) docs/API.md mention:

```
Note: The `CloudServer` implementation inherits common behaviors (authentication, rate limiting, security headers, instrumentation) from a `TemplateServer` base class. These behaviors are automatically applied to endpoints.
```

Misc notes & tips
-----------------
- Keep the repo's tests referencing `TemplateServer` while it stays local to avoid large refactoring work.
- When publishing the package, consider a small compatibility release (e.g., `0.1.0`) and maintain a deprecation note for the local module before removing it.
- If you use an internal package feed, store credentials in CI secret stores and update Docker build steps for authentication.

Questions for you
------------------
- Do you already have a package name and PyPI or internal registry planned for `TemplateServer`? If yes, I will include explicit package name references in this file.
- Do you prefer to keep `TemplateServer` as a local module until the package is published? (Strongly recommended during extraction)

If you'd like, I can now:
- Create these doc updates directly in the repo as a PR (I will base the changes on the `extract-template-server` branch), OR
- Keep this document as is for you to implement once the package is ready.

Notes
-----
- This document intentionally includes copy-paste ready snippets and a migration checklist to speed up applying updates once the `TemplateServer` package is published.
- If you want me to produce a PR with these doc updates or update tests to reflect the external package after publishing, tell me the package name and the preferred release cadence.
