"""tests/runtime/test_context_injector.py — ContextInjector behavior (Phase 12).

Verifies the three core invariants of the injection wrapper:
  1. Flag OFF → pure no-op (zero behavior change)
  2. Flag ON + router failure → graceful degrade (task unmodified, warning logged)
  3. Flag ON + router success → <cluster-context> block prepended to task.prompt
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from unittest import mock

import pytest


@dataclass
class _FakeTask:
    prompt: str = ""


@dataclass
class _FakeSection:
    source_type: str = "logs"
    content: str = "synthetic log line"


@dataclass
class _FakeBundle:
    sections: list
    token_total: int = 100

    def to_prompt_block(self) -> str:
        return "<cluster-context>\n## LOGS\nsynthetic log line\n</cluster-context>"


def test_inject_flag_off_is_noop() -> None:
    from core.runtime.context_injector import ContextInjector

    task = _FakeTask(prompt="do the thing")
    with mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "off"}):
        injector = ContextInjector()
        result = injector.inject(task, runtime_name="codex")

    assert result is task
    assert result.prompt == "do the thing"


def test_inject_router_failure_is_graceful() -> None:
    from core.runtime.context_injector import ContextInjector

    task = _FakeTask(prompt="do the thing")
    with mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "on"}):
        injector = ContextInjector()
        fake_router = mock.Mock()
        fake_router.route.side_effect = RuntimeError("tokenizer unavailable")
        injector._router = fake_router

        result = injector.inject(task, runtime_name="codex", phase="13")

    assert result.prompt == "do the thing"


def test_inject_success_prepends_cluster_context() -> None:
    from core.runtime.context_injector import ContextInjector

    task = _FakeTask(prompt="original prompt body")
    bundle = _FakeBundle(sections=[_FakeSection()], token_total=100)

    with mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "on"}):
        injector = ContextInjector()
        fake_router = mock.Mock()
        fake_router.route.return_value = bundle
        injector._router = fake_router

        result = injector.inject(task, runtime_name="codex", phase="13")

    assert "<cluster-context>" in result.prompt
    assert "original prompt body" in result.prompt
    assert result.prompt.index("<cluster-context>") < result.prompt.index("original prompt body")


def test_inject_empty_bundle_is_noop() -> None:
    from core.runtime.context_injector import ContextInjector

    task = _FakeTask(prompt="original prompt body")
    empty_bundle = _FakeBundle(sections=[], token_total=0)

    with mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "on"}):
        injector = ContextInjector()
        fake_router = mock.Mock()
        fake_router.route.return_value = empty_bundle
        injector._router = fake_router

        result = injector.inject(task, runtime_name="codex")

    assert result.prompt == "original prompt body"


def test_unknown_runtime_defaults_to_claude() -> None:
    from core.runtime.context_injector import ContextInjector, _RUNTIME_TO_MODEL

    # sanity: the 3 canonical runtimes map to themselves
    assert _RUNTIME_TO_MODEL["claude"] == "claude"
    assert _RUNTIME_TO_MODEL["codex"] == "codex"
    assert _RUNTIME_TO_MODEL["ollama"] == "ollama"

    task = _FakeTask(prompt="x")
    bundle = _FakeBundle(sections=[_FakeSection()], token_total=50)
    captured: dict = {}

    def _route(**kwargs):
        captured.update(kwargs)
        return bundle

    with mock.patch.dict(os.environ, {"BR3_AUTO_CONTEXT": "on"}):
        injector = ContextInjector()
        fake_router = mock.Mock()
        fake_router.route.side_effect = _route
        injector._router = fake_router
        injector.inject(task, runtime_name="unknown-runtime")

    assert captured.get("model") == "claude"
