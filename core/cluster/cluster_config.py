"""Cluster config helpers for node-aware BR3 services.

This module is the only place in Python below/cluster code that should read
`~/.buildrunner/cluster.json` directly. Downstream callers should import
`load_cluster_config()` or the small URL/host helpers here instead of
hardcoding node addresses.
"""

from __future__ import annotations

import getpass
import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_CLUSTER_JSON = Path.home() / ".buildrunner" / "cluster.json"


def load_cluster_config() -> dict[str, Any]:
    """Return the parsed cluster configuration.

    `BR3_CLUSTER_CONFIG` may override the default config path for tests.
    """
    cluster_json = Path(os.environ.get("BR3_CLUSTER_CONFIG", _DEFAULT_CLUSTER_JSON))
    return json.loads(cluster_json.read_text(encoding="utf-8"))


def get_node_config(node_name: str) -> dict[str, Any]:
    """Return a node entry from the cluster config."""
    config = load_cluster_config()
    nodes = config.get("nodes", {})
    node = nodes.get(node_name)
    if not isinstance(node, dict):
        raise KeyError(f"cluster.json missing node {node_name!r}")
    return node


def get_below_ollama_url() -> str:
    """Return the canonical Below Ollama base URL."""
    override = os.environ.get("BR3_BELOW_OLLAMA_URL")
    if override:
        return override.rstrip("/")

    node = get_node_config("below")
    host = node.get("host", "localhost")
    port = int(os.environ.get("BR3_BELOW_OLLAMA_PORT", "11434"))
    return f"http://{host}:{port}"


def get_jimmy_semantic_url() -> str:
    """Return the canonical Jimmy semantic-service URL."""
    override = os.environ.get("BR3_JIMMY_SEMANTIC_URL")
    if override:
        return override.rstrip("/")

    node = get_node_config("jimmy")
    services = node.get("services", {})
    semantic = services.get("semantic-search", {})
    url = semantic.get("url")
    if isinstance(url, str) and url:
        return url.rstrip("/")
    host = node.get("host", "localhost")
    port = int(node.get("port", 8100))
    return f"http://{host}:{port}"


def get_jimmy_ssh_target() -> str:
    """Return the SSH target for Jimmy."""
    override = os.environ.get("BR3_JIMMY_SSH_TARGET")
    if override:
        return override

    node = get_node_config("jimmy")
    ssh_user = node.get("ssh_user") or getpass.getuser()
    host = node.get("host", "localhost")
    return f"{ssh_user}@{host}"


def get_jimmy_research_root() -> str:
    """Return Jimmy's research-library root path."""
    override = os.environ.get("BR3_JIMMY_RESEARCH_ROOT")
    if override:
        return override

    node = get_node_config("jimmy")
    storage = node.get("storage", {})
    path = storage.get("research_library")
    if isinstance(path, str) and path:
        return path
    storage_root = node.get("storage_root") or storage.get("root")
    if isinstance(storage_root, str) and storage_root:
        return str(Path(storage_root) / "research-library")
    return str(Path.home() / "research-library")


def get_jimmy_br3_root() -> str:
    """Return Jimmy's BuildRunner checkout path."""
    override = os.environ.get("BR3_JIMMY_REPO_ROOT")
    if override:
        return override
    return "/home/byronhudson/repos/BuildRunner3"

