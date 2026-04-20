import pytest

from core.runtime.edit_normalizer import (
    build_normalized_edit_bundle,
    mark_conflicted_proposals,
    normalize_edits,
)


def test_normalize_claude_style_authoritative_edits():
    edits = normalize_edits(
        [
            {"type": "write_file", "path": "src/app.py", "content": "print('hi')\n"},
            {"type": "shell_action", "command": ["pytest", "-q"]},
        ],
        source_runtime="claude",
        authoritative=True,
        task_id="task-1",
    )

    assert edits[0].edit_type == "write_file"
    assert edits[0].path == "src/app.py"
    assert edits[1].edit_type == "shell_action"


def test_normalize_full_file_rewrite_and_unified_diff():
    edits = normalize_edits(
        [
            {"type": "full_file_rewrite", "path": "src/app.py", "content": "print('ok')\n"},
            {"type": "patch", "diff": "--- a/src/app.py\n+++ b/src/app.py\n@@\n-print('old')\n+print('new')\n"},
        ],
        source_runtime="codex",
        authoritative=True,
        task_id="task-1",
    )

    assert edits[0].edit_type == "write_file"
    assert edits[1].edit_type == "unified_diff"


def test_shadow_edits_become_advisory_only():
    edits = normalize_edits(
        [{"type": "write_file", "path": "src/app.py", "content": "print('shadow')\n"}],
        source_runtime="codex",
        authoritative=False,
        task_id="task-1",
    )

    assert edits[0].edit_type == "advisory_only"
    assert edits[0].proposal_kind == "write_file"
    assert edits[0].authoritative is False


def test_conflicted_proposals_fail_closed_on_same_file():
    first = normalize_edits(
        [{"type": "write_file", "path": "src/app.py", "content": "print('a')\n"}],
        source_runtime="claude",
        authoritative=False,
        task_id="task-1",
    )
    second = normalize_edits(
        [{"type": "write_file", "path": "src/app.py", "content": "print('b')\n"}],
        source_runtime="codex",
        authoritative=False,
        task_id="task-1",
    )

    conflict_state, edits = mark_conflicted_proposals("task-1", first + second)

    assert conflict_state == "conflicted_proposal"
    assert edits[0].conflict_state == "conflicted_proposal"
    assert edits[1].conflict_state == "conflicted_proposal"


def test_build_normalized_edit_bundle_detects_workspace_and_shell_changes():
    edits, observed_changes = build_normalized_edit_bundle(
        raw_edits=[{"type": "write_file", "path": "src/app.py", "content": "print('ok')\n"}],
        workspace_diff="+++ b/src/app.py\n",
        shell_actions=[{"command": "pytest -q", "touched_files": ["tests/test_app.py"]}],
        source_runtime="claude",
        authoritative=True,
        task_id="task-1",
    )

    assert edits[0].edit_type == "write_file"
    assert {change.path for change in observed_changes} == {"src/app.py", "tests/test_app.py"}


def test_unsupported_edit_type_is_rejected():
    with pytest.raises(ValueError, match="Unsupported edit type"):
        normalize_edits(
            [{"type": "mystery_edit", "path": "src/app.py"}],
            source_runtime="claude",
            authoritative=True,
            task_id="task-1",
        )
