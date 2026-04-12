Workflows
=========

This document details the CI/CD workflows and reusable actions to build and release Python servers using this template.
It focuses on the reusable actions unique to this project, which handle building and releasing the containerized application.

.. note::
   The repository includes workflows that reference actions from the ``template-python`` repository.
   For detailed information about these actions, refer to: https://javidahmed64592.github.io/template-python/workflows.html

Actions
-------

The following actions can be referenced from other repositories using ``javidahmed64592/python-template-server/.github/actions/{category}/{action}@main``.

Setup Actions
~~~~~~~~~~~~~

**check-frontend-exists**

- **Description:** Check if the frontend directory exists in the repository to conditionally execute frontend CI and build jobs.
- **Location:** ``check-frontend-exists/action.yml``
- **Outputs:**

  - ``exists``: Indicates whether the frontend directory exists

- **Steps:**

  - Checks for directory named ``<repository name>-frontend``
  - Sets output to ``true`` or ``false`` based on directory existence
  - Logs message if directory doesn't exist

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/setup/check-frontend-exists@main
       id: check-frontend

----

**setup-node**

- **Description:** Set up Node.js with npm cache and install dependencies.
- **Location:** ``setup-node/action.yml``
- **Steps:**

  - Uses the ``setup-node`` action
  - Install ``npm`` packages

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/setup/setup-node@main

CI Actions
~~~~~~~~~~

**frontend**

- **Description:** Runs frontend validation checks (type-checking, linting, formatting, testing) and uploads coverage reports.
- **Location:** ``frontend/action.yml``
- **Steps:**

  - Uses the ``setup-node`` action
  - Runs ``npm run type-check`` for type checking
  - Runs ``npm run lint`` for static code analysis
  - Runs ``npm run format`` to tidy up scripts
  - Runs ``npm run test:coverage`` for frontend unit tests
  - Uploads unit test coverage report

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/ci/frontend@main

Build Actions
~~~~~~~~~~~~~

**build-frontend**

- **Description:** Build the frontend and upload the build artifacts for use in other jobs.
- **Location:** ``build-frontend/action.yml``
- **Steps:**

  - Uses the ``setup-node`` action
  - Runs ``npm run build`` to build frontend static files
  - Uploads static files as build artifact

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/build/build-frontend@main

Docker Actions
~~~~~~~~~~~~~~

**build-start-services**

- **Description:** Creates ``.env`` file from ``.env.example`` and starts Docker Compose services.
- **Location:** ``build-start-services/action.yml``
- **Steps:**

  - Moves ``.env.example`` to ``.env``
  - Runs ``docker compose [build-args] up --build -d``
  - Sleeps for ``wait-seconds`` to allow services to start

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/docker/build-start-services@main
       with:
         wait-seconds: "5"
         build-args: ""

----

**show-logs**

- **Description:** Shows logs from a Docker Compose container.
- **Location:** ``show-logs/action.yml``
- **Steps:**

  - Displays logs using ``docker compose logs`` for the repository name

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/docker/show-logs@main

----

**check-containers**

- **Description:** Checks the server health by polling the `/api/health` endpoint.
- **Location:** ``check-containers/action.yml``
- **Steps:**

  - Polls the server's health endpoint at regular intervals until it returns a successful response or times out

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/docker/check-containers@main
       with:
         port: 443
         num-retries: "5"
         timeout-seconds: "5"

----

**stop-services**

- **Description:** Stops Docker Compose services and removes volumes and orphans.
- **Location:** ``stop-services/action.yml``
- **Steps:**

  - Stops Docker Compose services and removes volumes and orphans

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/docker/stop-services@main

----

**prepare-release**

- **Description:** Gets the package version, creates a release directory with essential files, builds a tarball, and uploads it as a workflow artifact.
- **Location:** ``prepare-release/action.yml``
- **Steps:**

  - Extracts version via ``uv run ci-pyproject-version``
  - Creates release directory and copies ``docker-compose.yml``, ``README.md``, ``LICENSE``, ``.env.example``
  - Creates compressed tarball
  - Uploads tarball as artifact named ``{PACKAGE_NAME}_release``

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/docker/prepare-release@main

----

**check-repo-name**

- **Description:** Compares the repository name against the package name in ``pyproject.toml`` to prevent template-derived repositories from accidentally publishing releases.
- **Location:** ``check-repo-name/action.yml``
- **Outputs:**

  - ``should_release`` - ``"true"`` if names match, ``"false"`` otherwise
  - ``package_name`` - Package name extracted from ``pyproject.toml``

- **Steps:**

  - Extracts package name via ``uv run ci-pyproject-name``
  - Compares repository name with package name
  - Sets outputs based on match result and package name

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/docker/check-repo-name@main
       id: check_repo_name

----

**get-version**

- **Description:** Extracts the version and tag from ``pyproject.toml``.
- **Location:** ``get-version/action.yml``
- **Outputs:**

  - ``version`` - Version string (e.g. ``1.2.3``)
  - ``tag`` - Version tag (e.g. ``v1.2.3``)

- **Steps:**

  - Extracts version via ``uv run ci-pyproject-version``

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/docker/get-version@main
       id: get_version

----

**check-tag**

- **Description:** Checks if a Git tag already exists for the given version to avoid duplicate releases.
- **Location:** ``check-tag/action.yml``
- **Outputs:**

  - ``tag_exists`` - ``"true"`` if the tag exists, ``"false"`` otherwise

- **Steps:**

  - Checks if tag exists using GitHub API

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/docker/check-tag@main
       id: check_tag
       with:
         tag: ${{ steps.get_version.outputs.tag }}

----

**generate-release-notes**

- **Description:** Substitutes placeholders in ``RELEASE-NOTES.md`` with actual values.
- **Location:** ``generate-release-notes/action.yml``
- **Inputs:**

  - ``version`` - Release version (without the v prefix)
  - ``package_name`` - Package name from ``pyproject.toml``

- **Steps:**

  - Substitutes ``{{VERSION}}``, ``{{PACKAGE_NAME}}``, and ``{{REPOSITORY}}`` placeholders
  - Repository is derived from GitHub context

**Usage:**

.. code-block:: yaml

   steps:
     - uses: javidahmed64592/python-template-server/.github/actions/docker/generate-release-notes@main
       with:
         version: ${{ steps.get_version.outputs.version }}
         package_name: ${{ steps.check_repo_name.outputs.package_name }}

----

Workflows
---------

The following workflows inherit all Python validation jobs from ``template-python`` and add frontend-specific validation.

CI Workflow
~~~~~~~~~~~

The CI workflow runs on pushes and pull requests to the ``main`` branch.

**Additional Jobs:**

- ``frontend`` - Conditionally executes validation checks on frontend if frontend directory exists

Build Workflow
~~~~~~~~~~~~~~

The Build workflow runs on pushes and pull requests to the ``main`` branch.
It extends the base ``template-python`` build process with optional frontend building.

**Additional Jobs:**

- ``build-frontend`` - Conditionally builds frontend and outputs existence flag

**Modified Jobs:**

- `build-wheel` - Enhanced to include frontend builds if the frontend exists

Docker Workflow
~~~~~~~~~~~~~~~

The Docker workflow runs on pushes and pull requests to the ``main`` branch, and supports manual dispatch.
It consists of jobs to build, verify, and publish the Docker image.

**Jobs:**

- ``build-docker`` - Builds the Docker image and verifies the server is healthy
- ``prepare-release`` - Packages the release tarball and uploads as artifact (depends on ``build-docker``)
- ``publish-release`` - Publishes the Docker image to GitHub Container Registry and creates a GitHub release (depends on ``prepare-release``, push to ``main`` only)
