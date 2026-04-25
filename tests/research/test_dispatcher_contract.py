from __future__ import annotations

import json
import os
import re
import subprocess
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOME = Path.home()
DISPATCH_SH = HOME / ".buildrunner" / "scripts" / "llm-dispatch.sh"
RESEARCH_MD = HOME / ".claude" / "commands" / "research.md"
ADVERSARIAL_REVIEW_SH = HOME / ".buildrunner" / "scripts" / "adversarial-review.sh"
CROSS_MODEL_REVIEW_PY = PROJECT_ROOT / "core" / "cluster" / "cross_model_review.py"
REQUIRED_CRITIQUE_KEYS = {
    "weakest_claims",
    "missing_perspectives",
    "hallucination_risks",
    "sources_to_recheck",
}


def run_command(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 20,
) -> subprocess.CompletedProcess[str]:
    base_env = os.environ.copy()
    if env:
        base_env.update(env)
    return subprocess.run(  # noqa: S603
        args,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=base_env,
    )


def run_dispatch(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 20,
) -> subprocess.CompletedProcess[str]:
    return run_command(["/bin/bash", str(DISPATCH_SH), *args], env=env, timeout=timeout)


def dispatch_help_text() -> str:
    result = run_dispatch(["codex", "--help"])
    return f"{result.stdout}\n{result.stderr}"


def run_reviewer_block() -> str:
    content = RESEARCH_MD.read_text()
    match = re.search(r"run_reviewer\(\)\s*\{(?P<body>.*?)^\}", content, re.MULTILINE | re.DOTALL)
    assert match, f"run_reviewer() block not found in {RESEARCH_MD}"
    return match.group("body")


def install_fake_codex(tmp_path: Path) -> Path:
    fake_codex = tmp_path / "codex"
    fake_codex.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            if [[ "${1:-}" == "--version" ]]; then
              echo "codex 0.48.0"
              exit 0
            fi

            if [[ "${1:-}" == "models" && "${2:-}" == "list" ]]; then
              printf 'gpt-5.5\\ngpt-5.4\\n'
              exit 0
            fi

            if [[ "${1:-}" == "exec" ]]; then
              cat >/dev/null
              cat <<'EOF'
            {"weakest_claims":[{"claim":"A","reason":"B","suggested_check":"C"},{"claim":"D","reason":"E","suggested_check":"F"},{"claim":"G","reason":"H","suggested_check":"I"}],"missing_perspectives":["ops"],"hallucination_risks":[],"sources_to_recheck":["https://example.com"]}
            Tokens used: 12 in, 34 out
            Cost: $0.0001
            EOF
              exit 0
            fi

            echo "unexpected args: $*" >&2
            exit 99
            """
        )
    )
    fake_codex.chmod(0o755)
    return fake_codex


def test_reviewer_skill_uses_supported_dispatch_contract() -> None:
    help_text = dispatch_help_text()
    block = run_reviewer_block()

    assert 'llm-dispatch.sh "$provider" --prompt-file "$REVIEWER_PROMPT_FILE"' in block
    assert 'cat "$REVIEWER_PROMPT_TEMPLATE" "$BODY_FILE" > "$REVIEWER_PROMPT_FILE"' in RESEARCH_MD.read_text()
    assert ".content | fromjson" in RESEARCH_MD.read_text()
    assert ".ok == true" in RESEARCH_MD.read_text()

    passed_flags = set(re.findall(r"--[a-z-]+", block))
    assert passed_flags == {"--prompt-file"}
    for flag in passed_flags:
        assert flag in help_text, f"{flag} missing from llm-dispatch.sh help output"

    assert "--provider" not in block
    assert "--role" not in block
    assert "--body-file" not in block


def test_codex_dispatch_envelope_matches_reviewer_parser(tmp_path: Path) -> None:
    prompt_file = tmp_path / "reviewer-prompt.txt"
    prompt_file.write_text("Return critique JSON only.")
    install_fake_codex(tmp_path)

    env = {
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "BR3_DATA_DB": str(tmp_path / "dispatcher.db"),
    }
    result = run_dispatch(["codex", "--prompt-file", str(prompt_file)], env=env)

    assert result.returncode == 0, result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is True
    assert envelope["provider"] == "codex"
    assert isinstance(envelope["content"], str)

    critique = json.loads(envelope["content"])
    assert REQUIRED_CRITIQUE_KEYS.issubset(critique)


def test_unknown_flag_returns_structured_error_json(tmp_path: Path) -> None:
    prompt_file = tmp_path / "reviewer-prompt.txt"
    prompt_file.write_text("Return critique JSON only.")

    result = run_dispatch(["codex", "--prompt-file", str(prompt_file), "--body-file", "body.md"])

    assert result.returncode == 2
    envelope = json.loads(result.stdout)
    assert envelope == {
        "ok": False,
        "provider": "codex",
        "error": "unknown_flag:--body-file",
    }
    assert "[llm-dispatch] Unknown flag:" not in result.stderr


def test_backward_compat_entrypoints_still_parse_flags() -> None:
    assert CROSS_MODEL_REVIEW_PY.exists(), f"missing {CROSS_MODEL_REVIEW_PY}"
    assert ADVERSARIAL_REVIEW_SH.exists(), f"missing {ADVERSARIAL_REVIEW_SH}"

    cross_model_help = run_command(["python3", str(CROSS_MODEL_REVIEW_PY), "--help"])
    assert cross_model_help.returncode == 0
    assert "--mode" in cross_model_help.stdout

    adversarial_review = run_command(["/bin/bash", str(ADVERSARIAL_REVIEW_SH), "--consensus"])
    assert adversarial_review.returncode == 1
    assert "Usage:" in adversarial_review.stderr

    help_text = dispatch_help_text()
    for path in (CROSS_MODEL_REVIEW_PY, ADVERSARIAL_REVIEW_SH):
        content = path.read_text()
        for invocation in re.findall(r"llm-dispatch\.sh[^\n]*", content):
            for flag in re.findall(r"--[a-z-]+", invocation):
                assert flag in help_text, f"{path} uses unsupported dispatcher flag {flag}"
