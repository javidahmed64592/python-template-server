"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import sys
from datetime import datetime
from pathlib import Path

from template_python.constants import SPHINX_EXTENSIONS, SPHINX_HTML_THEME
from template_python.workflows import (
    get_author_from_pyproject,
    get_name_from_pyproject,
    get_rst_prolog,
    get_version_from_pyproject,
)

# Add the project root to sys.path for autodoc
sys.path.insert(0, str(Path(__file__).parents[2].resolve()))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = get_name_from_pyproject().replace("-", " ").title()
copyright = f"{datetime.now().year}, {get_author_from_pyproject()}"  # noqa: A001
author = get_author_from_pyproject()
release = get_version_from_pyproject()
package_name = get_name_from_pyproject().replace("-", "_")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = SPHINX_EXTENSIONS

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

# Autosummary settings
autosummary_generate = True

# Intersphinx mapping to link to other projects
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

exclude_patterns: list[str] = []

# -- RST substitutions -------------------------------------------------------
# These variables are automatically available in all RST files as |variable_name|

substitutions_default_enabled = True
rst_prolog = get_rst_prolog(
    keys=["project_name", "package_name", "repo_name"],
    values=[project, package_name, get_name_from_pyproject()],
)

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = SPHINX_HTML_THEME
