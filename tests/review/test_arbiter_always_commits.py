import json

from core.cluster import arbiter


class _FakeBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeMessage:
    def __init__(self, text):
        self.content = [_FakeBlock(text)]


class _FakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _FakeAnthropic:
    def __init__(self, responses):
        self.messages = _FakeMessages(responses)


class _AlwaysFailAnthropic:
    def __init__(self, api_key=None):
        self.messages = self

    def create(self, **_kwargs):
        raise RuntimeError("500 upstream")


def _reviewers():
    return [
        {
            "name": "sonnet-4-6",
            "findings": [{"finding": "missing guard", "severity": "blocker", "fix_type": "fixable"}],
            "duration_ms": 11,
            "status": "ok",
        },
        {"name": "gpt-5.4", "findings": [], "duration_ms": 60000, "status": "timeout"},
    ]


def test_arbiter_error_commits_block(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".buildrunner").mkdir()
    failing_client = _FakeAnthropic([RuntimeError("500 first"), RuntimeError("500 second")])
    monkeypatch.setattr(arbiter, "Anthropic", lambda api_key=None: failing_client)

    result = arbiter.arbitrate("plan text", _reviewers(), {"plan_hash": "abc123"})

    assert result["verdict"] == "BLOCK"
    assert result["reason"] == "arbiter-error"
    assert result["fallback_logic"]
    assert result["last_opus_payload"]["attempt"] == 2
    assert len(failing_client.messages.calls) == 2


def test_circuit_open_after_three_consecutive_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".buildrunner").mkdir()
    monkeypatch.setattr(arbiter, "Anthropic", _AlwaysFailAnthropic)

    arbiter.arbitrate("plan one", _reviewers(), {"plan_hash": "one"})
    arbiter.arbitrate("plan two", _reviewers(), {"plan_hash": "two"})
    result = arbiter.arbitrate("plan three", _reviewers(), {"plan_hash": "three"})

    assert result["verdict"] == "BLOCK"
    assert result["reason"] == "circuit_open"
    assert result["circuit_state"] == "open"

    state_path = tmp_path / ".buildrunner" / "state" / "arbiter-circuit.json"
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["state"] == "open"
    assert (tmp_path / ".buildrunner" / "decisions.log").exists()


def test_success_captures_full_reasoning(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".buildrunner").mkdir()
    success_client = _FakeAnthropic([_FakeMessage('{"verdict":"PASS","reasoning":"All clear after comparing both reviewers."}')])
    monkeypatch.setattr(arbiter, "Anthropic", lambda api_key=None: success_client)

    result = arbiter.arbitrate("plan text", _reviewers(), {"plan_hash": "happy"})

    assert result["verdict"] == "PASS"
    assert result["arbiter"]["reasoning"] == "All clear after comparing both reviewers."
    assert result["arbiter"]["status"] == "ok"
    call = success_client.messages.calls[0]
    assert call["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert "temperature" not in call
    assert "budget_tokens" not in json.dumps(call)
