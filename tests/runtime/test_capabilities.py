from core.runtime.capabilities import CapabilityProfile
from core.runtime.codex_runtime import CodexRuntime
from core.runtime.runtime_registry import RuntimeRegistration


def test_capability_profile_preserves_known_flags_and_extra_metadata():
    profile = CapabilityProfile.from_legacy(
        {
            "review": True,
            "plan": True,
            "streaming": True,
            "shell": True,
            "browser": False,
            "isolated_workspace_only": True,
            "edit_formats": ["unified_diff"],
            "json_events": True,
            "dispatch_mode": "direct",
        }
    )

    assert profile.review is True
    assert profile.plan is True
    assert profile.streaming is True
    assert profile.shell is True
    assert profile.isolated_workspace_only is True
    assert profile.edit_formats == ["unified_diff"]
    assert profile.metadata == {"dispatch_mode": "direct"}


def test_runtime_registration_describe_uses_capability_profile():
    registration = RuntimeRegistration(name="codex", adapter=CodexRuntime(timeout_seconds=5), dispatch_mode="direct")

    description = registration.describe()

    assert description["runtime"] == "codex"
    assert description["backend"] == "codex-cli"
    assert description["dispatch_mode"] == "direct"
    assert description["capabilities"]["execution"] is True
    assert description["capabilities"]["browser"] is False
    assert description["capabilities"]["subagents"] is False


def test_codex_runtime_capability_profile_stays_bounded():
    profile = CodexRuntime(timeout_seconds=5).get_capability_profile()

    assert profile.review is True
    assert profile.plan is True
    assert profile.execution is True
    assert profile.browser is False
    assert profile.subagents is False
    assert profile.cluster_suitable is True
    assert profile.isolated_workspace_only is True
    assert "advisory_only" in profile.edit_formats
