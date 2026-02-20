"""Unit tests for non-interactive LLM runner."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from kubeagle.optimizer.llm_cli_runner import (
    LLMProvider,
    _claude_agent_sdk_available,
    _summarize_tool_input,
    detect_llm_cli_capabilities,
    provider_supports_direct_edit,
    run_llm_cli_non_interactive,
    run_llm_direct_edit,
    run_llm_structured_patch_non_interactive,
)


def test_run_codex_non_interactive_uses_exec_and_returns_last_message(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Codex runner should call `codex exec` non-interactively and return direct text."""
    captured_command: list[str] = []
    captured_kwargs: dict[str, object] = {}

    def _fake_run(command, **kwargs):
        captured_command.clear()
        captured_command.extend(command)
        captured_kwargs.clear()
        captured_kwargs.update(kwargs)
        out_index = command.index("--output-last-message")
        out_path = Path(command[out_index + 1])
        out_path.write_text("direct codex response", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="noise", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = run_llm_cli_non_interactive(
        provider=LLMProvider.CODEX,
        prompt="Generate patch",
        cwd=tmp_path,
    )

    assert result.ok is True
    assert result.response_text == "direct codex response"
    assert captured_command[:2] == ["codex", "exec"]
    assert "--ephemeral" in captured_command
    assert captured_command[-1] == "-"
    assert captured_kwargs["input"] == "Generate patch"


def test_run_claude_non_interactive_uses_agent_sdk_and_returns_text(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Claude non-interactive runner should use Agent SDK and return response text."""
    seen: dict[str, object] = {}

    class FakeTextBlock:
        def __init__(self, text: str):
            self.text = text

    class FakeAssistantMessage:
        def __init__(self, content: list[object]):
            self.content = content

    class FakeResultMessage:
        def __init__(self):
            self.is_error = False
            self.result = None

    async def _fake_query(prompt, options):
        seen["prompt"] = prompt
        seen["options"] = options
        yield FakeAssistantMessage([FakeTextBlock("direct claude response")])
        yield FakeResultMessage()

    fake_sdk = SimpleNamespace(
        query=_fake_query,
        ClaudeAgentOptions=lambda **kw: SimpleNamespace(**kw),
        AssistantMessage=FakeAssistantMessage,
        ResultMessage=FakeResultMessage,
        TextBlock=FakeTextBlock,
    )

    original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def _mock_import(name, *args, **kwargs):
        if name == "claude_agent_sdk":
            return fake_sdk
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _mock_import)

    result = run_llm_cli_non_interactive(
        provider=LLMProvider.CLAUDE,
        prompt="Generate patch",
        cwd=tmp_path,
    )

    assert result.ok is True
    assert result.response_text == "direct claude response"
    assert result.command[0] == "claude-agent-sdk:default"
    assert seen["prompt"] == "Generate patch"
    options = seen["options"]
    assert getattr(options, "cwd", "") == str(tmp_path)
    assert getattr(options, "allowed_tools", None) == []


def test_run_claude_non_interactive_returns_error_when_no_sdk(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Claude non-interactive runner should fail when Agent SDK is unavailable."""
    original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def _mock_import(name, *args, **kwargs):
        if name == "claude_agent_sdk":
            raise ImportError("No module named 'claude_agent_sdk'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _mock_import)

    result = run_llm_cli_non_interactive(
        provider=LLMProvider.CLAUDE,
        prompt="Generate patch",
        cwd=tmp_path,
    )

    assert result.ok is False
    assert result.exit_code == 127
    assert "not installed" in result.error_message


def test_run_llm_cli_non_interactive_returns_error_on_missing_binary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Missing CLI binary should return structured error."""
    def _fake_run(*args, **kwargs):
        _ = args, kwargs
        raise FileNotFoundError("codex not found")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = run_llm_cli_non_interactive(
        provider=LLMProvider.CODEX,
        prompt="hello",
        cwd=tmp_path,
        model="o3",
        timeout_seconds=1,
    )
    assert result.ok is False
    assert result.exit_code == 127
    assert result.error_message


def test_run_llm_structured_patch_non_interactive_parses_contract(monkeypatch) -> None:
    """Structured runner should parse normalized JSON output into typed payload."""
    def _fake_runner(**kwargs):
        _ = kwargs
        return SimpleNamespace(
            ok=True,
            provider=LLMProvider.CLAUDE,
            command=["claude-agent-sdk:default"],
            response_text=(
                '{"schema_version":"patch_response.v1","result":"ok","summary":"done",'
                '"patches":[{"file":"templates/deployment.yaml","purpose":"wire","unified_diff":"--- a/templates/deployment.yaml\\n+++ b/templates/deployment.yaml\\n@@ -1,1 +1,2 @@\\n+livenessProbe:"}],'
                '"warnings":[],"error":""}'
            ),
            stderr="",
            error_message="",
            exit_code=0,
        )

    monkeypatch.setattr(
        "kubeagle.optimizer.llm_cli_runner.run_llm_cli_non_interactive",
        _fake_runner,
    )

    result = run_llm_structured_patch_non_interactive(
        provider=LLMProvider.CLAUDE,
        prompt="generate patch",
    )

    assert result.ok is True
    assert result.parsed is not None
    assert result.parsed.result == "ok"
    assert result.parsed.patches[0].file == "templates/deployment.yaml"


def test_run_llm_structured_patch_non_interactive_reports_parse_error(monkeypatch) -> None:
    """Structured runner should expose parse_error for malformed output."""
    def _fake_runner(**kwargs):
        _ = kwargs
        return SimpleNamespace(
            ok=True,
            provider=LLMProvider.CODEX,
            command=["codex", "exec"],
            response_text="not-json",
            stderr="",
            error_message="",
            exit_code=0,
        )

    monkeypatch.setattr(
        "kubeagle.optimizer.llm_cli_runner.run_llm_cli_non_interactive",
        _fake_runner,
    )

    result = run_llm_structured_patch_non_interactive(
        provider=LLMProvider.CODEX,
        prompt="generate patch",
    )

    assert result.ok is False
    assert result.parsed is None
    assert result.parse_error


def test_detect_llm_cli_capabilities(monkeypatch) -> None:
    """Capability detection should reflect provider backend availability."""
    monkeypatch.setattr(
        "kubeagle.optimizer.llm_cli_runner.shutil.which",
        lambda binary: "/usr/bin/mock" if binary == "codex" else None,
    )
    monkeypatch.setattr(
        "kubeagle.optimizer.llm_cli_runner._claude_agent_sdk_available",
        lambda: False,
    )
    capabilities = detect_llm_cli_capabilities()
    assert capabilities[LLMProvider.CODEX] is True
    assert capabilities[LLMProvider.CLAUDE] is False
    assert provider_supports_direct_edit(LLMProvider.CODEX) is True
    assert provider_supports_direct_edit(LLMProvider.CLAUDE) is False


def test_run_llm_direct_edit_detects_changed_files(monkeypatch, tmp_path: Path) -> None:
    """Direct-edit runner should detect in-place file changes under cwd."""
    target = tmp_path / "values.yaml"
    target.write_text("replicaCount: 1\n", encoding="utf-8")
    captured_command: list[str] = []

    def _fake_run(command, **kwargs):
        captured_command.clear()
        captured_command.extend(command)
        _ = command, kwargs
        target.write_text("replicaCount: 2\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="done", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = run_llm_direct_edit(
        provider=LLMProvider.CODEX,
        prompt="edit files",
        cwd=tmp_path,
        timeout_seconds=5,
    )

    assert result.ok is True
    assert "values.yaml" in result.changed_rel_paths
    assert "Changed Files (1)" in result.log_text
    assert "--full-auto" in captured_command


def test_run_llm_direct_edit_claude_uses_agent_sdk_when_available(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Claude direct-edit should use Agent SDK and detect file changes."""
    target = tmp_path / "values.yaml"
    target.write_text("replicaCount: 1\n", encoding="utf-8")

    # Fake SDK types
    class FakeTextBlock:
        def __init__(self, text: str):
            self.text = text

    class FakeToolUseBlock:
        def __init__(self, name: str, tool_input: dict):
            self.name = name
            self.id = "tool-1"
            self.input = tool_input

    class FakeAssistantMessage:
        def __init__(self, content: list):
            self.content = content
            self.model = "sonnet"

    class FakeResultMessage:
        def __init__(self):
            self.session_id = "test-session"
            self.num_turns = 2
            self.total_cost_usd = 0.01
            self.duration_ms = 1000
            self.is_error = False
            self.result = None

    async def _fake_query(prompt, options):
        # Simulate the SDK editing the file
        target.write_text("replicaCount: 3\n", encoding="utf-8")
        yield FakeAssistantMessage([
            FakeTextBlock("I'll edit the file."),
            FakeToolUseBlock("Edit", {"file_path": str(target)}),
        ])
        yield FakeAssistantMessage([
            FakeTextBlock("Done editing."),
        ])
        yield FakeResultMessage()

    # Mock the import inside _run_claude_agent_sdk_direct_edit
    fake_sdk = SimpleNamespace(
        query=_fake_query,
        ClaudeAgentOptions=lambda **kw: SimpleNamespace(**kw),
        AssistantMessage=FakeAssistantMessage,
        ResultMessage=FakeResultMessage,
        TextBlock=FakeTextBlock,
        ToolUseBlock=FakeToolUseBlock,
    )

    original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

    def _mock_import(name, *args, **kwargs):
        if name == "claude_agent_sdk":
            return fake_sdk
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _mock_import)

    result = run_llm_direct_edit(
        provider=LLMProvider.CLAUDE,
        prompt="increase replicas",
        cwd=tmp_path,
        timeout_seconds=30,
    )

    assert result.ok is True
    assert "values.yaml" in result.changed_rel_paths
    assert "Agent SDK" in result.log_text
    assert "Tool: Edit" in result.log_text


def test_run_llm_direct_edit_claude_returns_error_when_no_sdk(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Claude direct-edit should return error when SDK is not installed."""
    (tmp_path / "values.yaml").write_text("a: 1\n", encoding="utf-8")

    # Force ImportError for claude_agent_sdk
    original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

    def _mock_import(name, *args, **kwargs):
        if name == "claude_agent_sdk":
            raise ImportError("No module named 'claude_agent_sdk'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _mock_import)

    result = run_llm_direct_edit(
        provider=LLMProvider.CLAUDE,
        prompt="edit",
        cwd=tmp_path,
        timeout_seconds=5,
    )

    assert result.ok is False
    assert "not installed" in result.error_message


def test_detect_llm_cli_capabilities_includes_agent_sdk(monkeypatch) -> None:
    """Claude should be detected as available when Agent SDK is installed."""
    monkeypatch.setattr(
        "kubeagle.optimizer.llm_cli_runner.shutil.which",
        lambda binary: None,
    )
    monkeypatch.setattr(
        "kubeagle.optimizer.llm_cli_runner._claude_agent_sdk_available",
        lambda: True,
    )
    capabilities = detect_llm_cli_capabilities()
    assert capabilities[LLMProvider.CLAUDE] is True
    assert capabilities[LLMProvider.CODEX] is False


def test_claude_agent_sdk_available_false_when_not_installed(monkeypatch) -> None:
    """_claude_agent_sdk_available should return False when package is not importable."""
    original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

    def _mock_import(name, *args, **kwargs):
        if name == "claude_agent_sdk":
            raise ImportError("No module named 'claude_agent_sdk'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _mock_import)
    assert _claude_agent_sdk_available() is False


def test_run_llm_direct_edit_claude_agent_sdk_timeout(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Claude Agent SDK should respect timeout and return error instead of hanging."""
    (tmp_path / "values.yaml").write_text("a: 1\n", encoding="utf-8")

    # Fake SDK that hangs forever
    import asyncio as _asyncio

    class FakeAssistantMessage:
        def __init__(self, content):
            self.content = content
            self.model = "sonnet"

    class FakeResultMessage:
        pass

    class FakeTextBlock:
        def __init__(self, text):
            self.text = text

    class FakeToolUseBlock:
        pass

    async def _hanging_query(prompt, options):
        # Yield one message then hang forever
        yield FakeAssistantMessage([FakeTextBlock("Starting...")])
        await _asyncio.sleep(999)

    fake_sdk = SimpleNamespace(
        query=_hanging_query,
        ClaudeAgentOptions=lambda **kw: SimpleNamespace(**kw),
        AssistantMessage=FakeAssistantMessage,
        ResultMessage=FakeResultMessage,
        TextBlock=FakeTextBlock,
        ToolUseBlock=FakeToolUseBlock,
    )

    original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

    def _mock_import(name, *args, **kwargs):
        if name == "claude_agent_sdk":
            return fake_sdk
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _mock_import)

    result = run_llm_direct_edit(
        provider=LLMProvider.CLAUDE,
        prompt="edit",
        cwd=tmp_path,
        timeout_seconds=2,
    )

    assert result.ok is False
    assert "timed out" in result.error_message.lower()


def test_summarize_tool_input_formats_path_and_content() -> None:
    """_summarize_tool_input should extract file_path or command from dict."""
    assert _summarize_tool_input({"file_path": "/tmp/values.yaml"}) == "/tmp/values.yaml"
    assert _summarize_tool_input({"command": "echo hello"}) == "echo hello"
    assert _summarize_tool_input(None) == ""
    assert _summarize_tool_input("raw string") == "raw string"
    # dict without file_path or command falls back to str repr
    result = _summarize_tool_input({"key": "value"})
    assert "key" in result
