"""tests/cluster/test_context_router_no_side_effects.py — Phase 1 TDD tests.

Unit test requirement from BUILD spec:
  `import api.routes.context` must NOT instantiate FastAPI app.
  Assert via importlib + attribute check.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys

import pytest


def test_import_context_does_not_create_fastapi_app():
    """Importing api.routes.context must NOT create a FastAPI app instance.

    The module should only define an APIRouter (router) with NO top-level 'app'
    attribute that is a FastAPI instance.
    """
    # Remove from sys.modules if already imported so we get a fresh import
    mod_name = "api.routes.context"
    for key in list(sys.modules.keys()):
        if "api.routes.context" in key:
            del sys.modules[key]

    # Import the module
    mod = importlib.import_module(mod_name)

    # Must NOT have a module-level 'app' attribute that is a FastAPI instance
    assert not hasattr(mod, "app"), (
        "api.routes.context must NOT have a module-level 'app' attribute. "
        "A FastAPI app was detected. Move app bootstrap to api/services/context_api_standalone.py."
    )


def test_context_module_has_router():
    """api.routes.context must expose an APIRouter named 'router'."""
    mod_name = "api.routes.context"
    for key in list(sys.modules.keys()):
        if "api.routes.context" in key:
            del sys.modules[key]

    mod = importlib.import_module(mod_name)

    assert hasattr(mod, "router"), (
        "api.routes.context must expose an APIRouter named 'router'"
    )

    # Verify it's an APIRouter, not a FastAPI app
    from fastapi import APIRouter
    from fastapi import FastAPI
    assert isinstance(mod.router, APIRouter), (
        f"Expected APIRouter, got {type(mod.router)}"
    )
    assert not isinstance(mod.router, FastAPI), (
        "router must be APIRouter, not FastAPI app"
    )


def test_context_module_router_has_context_prefix():
    """The router in api.routes.context must have prefix='/context'."""
    mod_name = "api.routes.context"
    for key in list(sys.modules.keys()):
        if "api.routes.context" in key:
            del sys.modules[key]

    mod = importlib.import_module(mod_name)
    assert hasattr(mod, "router"), "api.routes.context must expose 'router'"
    assert mod.router.prefix == "/context", (
        f"Expected router prefix '/context', got '{mod.router.prefix}'"
    )


def test_standalone_entrypoint_exists():
    """api/services/context_api_standalone.py must exist."""
    import os
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    standalone_path = os.path.join(
        repo_root, "api", "services", "context_api_standalone.py"
    )
    assert os.path.exists(standalone_path), (
        f"Standalone entrypoint not found: {standalone_path}"
    )


def test_standalone_has_main_guard():
    """api/services/context_api_standalone.py must have 'if __name__ == \"__main__\"' guard."""
    import os
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    standalone_path = os.path.join(
        repo_root, "api", "services", "context_api_standalone.py"
    )
    with open(standalone_path) as f:
        content = f.read()
    assert '__name__ == "__main__"' in content or "__name__ == '__main__'" in content, (
        "context_api_standalone.py must have if __name__ == '__main__' guard"
    )


def test_node_semantic_mounts_context_router():
    """core/cluster/node_semantic.py must mount context_router."""
    import os
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    node_path = os.path.join(repo_root, "core", "cluster", "node_semantic.py")
    with open(node_path) as f:
        content = f.read()
    assert "context_router" in content or "context.router" in content, (
        "core/cluster/node_semantic.py must include_router for context_router"
    )
    assert "include_router" in content, (
        "core/cluster/node_semantic.py must call app.include_router"
    )
