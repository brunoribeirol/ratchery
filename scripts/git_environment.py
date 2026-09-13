"""Build a Git subprocess environment without repository-routing overrides."""
from __future__ import annotations

import os

GIT_REPOSITORY_OVERRIDES = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
    "GIT_DIR",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_EXEC_PATH",
    "GIT_GRAFT_FILE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_INTERNAL_SUPER_PREFIX",
    "GIT_NAMESPACE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
    "GIT_REPLACE_REF_BASE",
    "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
}


def clean_git_environment() -> dict[str, str]:
    """Preserve normal process settings while removing Git routing/config injection."""
    environment = os.environ.copy()
    for variable in list(environment):
        if variable in GIT_REPOSITORY_OVERRIDES or variable.startswith("GIT_CONFIG_"):
            environment.pop(variable, None)
    return environment
