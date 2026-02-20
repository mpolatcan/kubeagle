"""Non-interactive runners for Codex CLI and Claude Agent SDK."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from kubeagle.optimizer.llm_patch_protocol import (
    StructuredPatchResponse,
    parse_structured_patch_response,
)

_AGENT_SDK_MAX_TURNS = 10


class LLMProvider(str, Enum):
    """Supported non-interactive CLI providers."""

    CODEX = "codex"
    CLAUDE = "claude"


@dataclass(slots=True)
class LLMCLIResult:
    """Result from a non-interactive LLM CLI execution."""

    ok: bool
    provider: LLMProvider
    command: list[str] = field(default_factory=list)
    response_text: str = ""
    stderr: str = ""
    error_message: str = ""
    exit_code: int = 0


@dataclass(slots=True)
class LLMStructuredPatchResult:
    """Structured patch execution and parsing result."""

    ok: bool
    provider: LLMProvider
    cli_result: LLMCLIResult
    parsed: StructuredPatchResponse | None = None
    parse_error: str = ""


@dataclass(slots=True)
class LLMDirectEditResult:
    """Result of provider-driven direct file edits in an existing workspace."""

    ok: bool
    provider: LLMProvider
    command: list[str] = field(default_factory=list)
    log_text: str = ""
    attempts: int = 1
    changed_rel_paths: list[str] = field(default_factory=list)
    error_message: str = ""
    stdout_tail: str = ""
    stderr_tail: str = ""


def _claude_agent_sdk_available() -> bool:
    """Return True if the claude-agent-sdk package is importable."""
    try:
        from claude_agent_sdk import query as _q  # noqa: F401

        return True
    except Exception:
        return False


def detect_llm_cli_capabilities() -> dict[LLMProvider, bool]:
    """Detect whether each provider backend is available."""
    return {
        LLMProvider.CODEX: shutil.which("codex") is not None,
        LLMProvider.CLAUDE: _claude_agent_sdk_available(),
    }


def provider_supports_direct_edit(provider: LLMProvider) -> bool:
    """Return whether provider appears available for direct-edit execution."""
    return detect_llm_cli_capabilities().get(provider, False)


def run_llm_direct_edit(
    *,
    provider: LLMProvider,
    prompt: str,
    cwd: Path,
    timeout_seconds: int = 180,
    model: str | None = None,
    attempts: int = 1,
) -> LLMDirectEditResult:
    """Run provider against workspace and detect file changes done in place."""
    working_dir = cwd.expanduser().resolve()
    if not working_dir.exists() or not working_dir.is_dir():
        return LLMDirectEditResult(
            ok=False,
            provider=provider,
            attempts=max(1, int(attempts)),
            error_message=f"Direct-edit working directory not found: {working_dir}",
            log_text=f"Direct-edit working directory not found: {working_dir}",
        )

    if provider == LLMProvider.CODEX:
        command = [
            "codex",
            "exec",
            "--ephemeral",
            "--color",
            "never",
            "--skip-git-repo-check",
            "--full-auto",
        ]
        if model:
            command.extend(["--model", model])
        command.extend(["--cd", str(working_dir), "-"])
        return _run_direct_edit_subprocess(
            provider=provider,
            command=command,
            prompt=prompt,
            working_dir=working_dir,
            timeout_seconds=timeout_seconds,
            attempts=attempts,
        )

    if provider == LLMProvider.CLAUDE:
        before_snapshot = _snapshot_tree_hashes(working_dir)
        result = _run_claude_agent_sdk_direct_edit(
            prompt=prompt,
            working_dir=working_dir,
            model=model,
            max_turns=_AGENT_SDK_MAX_TURNS,
            timeout_seconds=timeout_seconds,
        )
        if not result.ok:
            return result
        after_snapshot = _snapshot_tree_hashes(working_dir)
        result.changed_rel_paths = _collect_changed_paths(before_snapshot, after_snapshot)
        result.attempts = max(1, int(attempts))
        return result

    return LLMDirectEditResult(
        ok=False,
        provider=provider,
        attempts=max(1, int(attempts)),
        error_message=f"Unsupported provider: {provider}",
        log_text=f"Unsupported provider: {provider}",
    )


def _run_direct_edit_subprocess(
    *,
    provider: LLMProvider,
    command: list[str],
    prompt: str,
    working_dir: Path,
    timeout_seconds: int,
    attempts: int,
) -> LLMDirectEditResult:
    """Execute a direct-edit CLI command via subprocess with snapshot diffing."""
    before_snapshot = _snapshot_tree_hashes(working_dir)
    try:
        process = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_seconds)),
            check=False,
            cwd=str(working_dir),
            env=_non_interactive_env(),
        )
    except FileNotFoundError as exc:
        return LLMDirectEditResult(
            ok=False,
            provider=provider,
            command=command,
            attempts=max(1, int(attempts)),
            error_message=str(exc),
            log_text=f"Binary not found: {exc!s}",
        )
    except subprocess.TimeoutExpired as exc:
        stdout_tail = _tail_text(_safe_text(exc.stdout))
        stderr_tail = _tail_text(_safe_text(exc.stderr))
        return LLMDirectEditResult(
            ok=False,
            provider=provider,
            command=command,
            attempts=max(1, int(attempts)),
            error_message=f"{provider.value} timed out after {timeout_seconds}s",
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            log_text=_build_direct_edit_log(
                provider=provider,
                command=command,
                cwd=working_dir,
                exit_code=124,
                changed_rel_paths=[],
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                error_message=f"{provider.value} timed out after {timeout_seconds}s",
                attempts=max(1, int(attempts)),
            ),
        )

    after_snapshot = _snapshot_tree_hashes(working_dir)
    changed_rel_paths = _collect_changed_paths(before_snapshot, after_snapshot)
    stdout_tail = _tail_text(process.stdout or "")
    stderr_tail = _tail_text(process.stderr or "")
    error_message = ""
    if process.returncode != 0:
        error_message = (
            (process.stderr or process.stdout or "").strip()
            or f"{provider.value} exited with code {process.returncode}"
        )
    return LLMDirectEditResult(
        ok=process.returncode == 0,
        provider=provider,
        command=command,
        attempts=max(1, int(attempts)),
        changed_rel_paths=changed_rel_paths,
        error_message=error_message,
        stdout_tail=stdout_tail,
        stderr_tail=stderr_tail,
        log_text=_build_direct_edit_log(
            provider=provider,
            command=command,
            cwd=working_dir,
            exit_code=int(process.returncode),
            changed_rel_paths=changed_rel_paths,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            error_message=error_message,
            attempts=max(1, int(attempts)),
        ),
    )


def _run_claude_agent_sdk_direct_edit(
    *,
    prompt: str,
    working_dir: Path,
    model: str | None,
    max_turns: int = _AGENT_SDK_MAX_TURNS,
    timeout_seconds: int = 180,
) -> LLMDirectEditResult:
    """Run Claude Agent SDK with Read/Write/Edit tools for direct file edits."""
    try:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
            query,
        )
    except ImportError:
        return LLMDirectEditResult(
            ok=False,
            provider=LLMProvider.CLAUDE,
            error_message="claude-agent-sdk not installed.",
        )

    options = ClaudeAgentOptions(
        model=model,
        cwd=str(working_dir),
        allowed_tools=["Read", "Write", "Edit"],
        permission_mode="bypassPermissions",
        max_turns=max(1, max_turns),
    )

    log_lines: list[str] = [
        "Provider: claude (Agent SDK)",
        f"Model: {model or 'default'}",
        f"CWD: {working_dir}",
    ]
    final_text: list[str] = []
    result_msg: ResultMessage | None = None

    async def _run() -> None:
        nonlocal result_msg
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        final_text.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        log_lines.append(f"  Tool: {block.name}({_summarize_tool_input(block.input)})")
            elif isinstance(message, ResultMessage):
                result_msg = message

    effective_timeout = max(10, int(timeout_seconds))
    try:
        asyncio.run(asyncio.wait_for(_run(), timeout=float(effective_timeout)))
    except asyncio.TimeoutError:
        return LLMDirectEditResult(
            ok=False,
            provider=LLMProvider.CLAUDE,
            error_message=f"Agent SDK timed out after {effective_timeout}s",
            log_text="\n".join(log_lines),
        )
    except Exception as exc:
        return LLMDirectEditResult(
            ok=False,
            provider=LLMProvider.CLAUDE,
            error_message=str(exc),
            log_text="\n".join(log_lines),
        )

    if result_msg is not None:
        cost = getattr(result_msg, "total_cost_usd", None) or 0
        turns = getattr(result_msg, "num_turns", "?")
        log_lines.append(f"Turns: {turns}, Cost: ${cost:.4f}")
        is_error = getattr(result_msg, "is_error", False)
        if is_error:
            error_text = getattr(result_msg, "result", "") or "Agent SDK error"
            return LLMDirectEditResult(
                ok=False,
                provider=LLMProvider.CLAUDE,
                error_message=str(error_text),
                log_text="\n".join(log_lines),
            )

    return LLMDirectEditResult(
        ok=True,
        provider=LLMProvider.CLAUDE,
        command=[f"claude-agent-sdk:{model or 'default'}"],
        log_text="\n".join(log_lines),
        stdout_tail=_tail_text("\n".join(final_text)),
    )


def _summarize_tool_input(tool_input: dict | str | None) -> str:
    """Format tool input for log display."""
    if not tool_input:
        return ""
    if isinstance(tool_input, str):
        return tool_input[:80]
    if isinstance(tool_input, dict):
        if "file_path" in tool_input:
            return str(tool_input["file_path"])
        if "command" in tool_input:
            cmd = tool_input["command"]
            return cmd[:80] if isinstance(cmd, str) else str(cmd)[:80]
        return str(tool_input)[:80]
    return str(tool_input)[:80]


def run_llm_cli_non_interactive(
    *,
    provider: LLMProvider,
    prompt: str,
    timeout_seconds: int = 120,
    cwd: Path | None = None,
    model: str | None = None,
) -> LLMCLIResult:
    """Run provider CLI in non-interactive mode and return direct response text."""
    working_dir = cwd.expanduser().resolve() if cwd is not None else None
    if provider == LLMProvider.CODEX:
        return _run_codex_non_interactive(
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            cwd=working_dir,
            model=model,
        )
    if provider == LLMProvider.CLAUDE:
        return _run_claude_agent_sdk_non_interactive(
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            cwd=working_dir,
            model=model,
        )
    return LLMCLIResult(
        ok=False,
        provider=provider,
        error_message=f"Unsupported provider: {provider}",
        exit_code=2,
    )


def _run_codex_non_interactive(
    *,
    prompt: str,
    timeout_seconds: int,
    cwd: Path | None,
    model: str | None,
) -> LLMCLIResult:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="kubeagle-codex-last-message-",
        suffix=".txt",
        delete=False,
    ) as tmp_output:
        output_path = Path(tmp_output.name)

    command = [
        "codex",
        "exec",
        "--ephemeral",
        "--color",
        "never",
        "--skip-git-repo-check",
        "--output-last-message",
        str(output_path),
    ]
    if model:
        command.extend(["--model", model])
    if cwd is not None:
        command.extend(["--cd", str(cwd)])
    command.append("-")

    try:
        process = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_seconds)),
            check=False,
            cwd=str(cwd) if cwd is not None else None,
            env=_non_interactive_env(),
        )
    except FileNotFoundError as exc:
        output_path.unlink(missing_ok=True)
        return LLMCLIResult(
            ok=False,
            provider=LLMProvider.CODEX,
            command=command,
            error_message=str(exc),
            exit_code=127,
        )
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        return LLMCLIResult(
            ok=False,
            provider=LLMProvider.CODEX,
            command=command,
            stderr=_safe_text(exc.stderr),
            error_message=f"codex command timed out after {timeout_seconds}s",
            exit_code=124,
        )

    response_text = ""
    with_output = output_path
    if with_output.exists():
        with_output_text = with_output.read_text(encoding="utf-8").strip()
        response_text = with_output_text
    with_output.unlink(missing_ok=True)
    if not response_text:
        response_text = (process.stdout or "").strip()

    if process.returncode != 0:
        return LLMCLIResult(
            ok=False,
            provider=LLMProvider.CODEX,
            command=command,
            response_text=response_text,
            stderr=(process.stderr or "").strip(),
            error_message=((process.stderr or process.stdout) or "").strip()
            or f"codex exited with code {process.returncode}",
            exit_code=process.returncode,
        )

    return LLMCLIResult(
        ok=True,
        provider=LLMProvider.CODEX,
        command=command,
        response_text=response_text,
        stderr=(process.stderr or "").strip(),
        exit_code=process.returncode,
    )


def _run_claude_agent_sdk_non_interactive(
    *,
    prompt: str,
    timeout_seconds: int,
    cwd: Path | None,
    model: str | None,
) -> LLMCLIResult:
    """Run Claude via Agent SDK for non-interactive text generation."""
    try:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            TextBlock,
            query,
        )
    except ImportError:
        return LLMCLIResult(
            ok=False,
            provider=LLMProvider.CLAUDE,
            command=[f"claude-agent-sdk:{model or 'default'}"],
            error_message="claude-agent-sdk not installed.",
            exit_code=127,
        )

    command = [f"claude-agent-sdk:{model or 'default'}"]
    resolved_cwd = cwd or Path.cwd()
    options = ClaudeAgentOptions(
        model=model,
        cwd=str(resolved_cwd),
        allowed_tools=[],
        permission_mode="bypassPermissions",
        max_turns=max(1, _AGENT_SDK_MAX_TURNS),
    )

    final_text: list[str] = []
    result_msg: ResultMessage | None = None

    async def _run() -> None:
        nonlocal result_msg
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        final_text.append(block.text)
            elif isinstance(message, ResultMessage):
                result_msg = message

    effective_timeout = max(10, int(timeout_seconds))
    try:
        asyncio.run(asyncio.wait_for(_run(), timeout=float(effective_timeout)))
    except asyncio.TimeoutError:
        return LLMCLIResult(
            ok=False,
            provider=LLMProvider.CLAUDE,
            command=command,
            error_message=f"Claude Agent SDK timed out after {effective_timeout}s",
            exit_code=124,
        )
    except Exception as exc:
        return LLMCLIResult(
            ok=False,
            provider=LLMProvider.CLAUDE,
            command=command,
            error_message=str(exc),
            exit_code=1,
        )

    if result_msg is not None and bool(getattr(result_msg, "is_error", False)):
        error_text = str(getattr(result_msg, "result", "") or "Agent SDK error").strip()
        return LLMCLIResult(
            ok=False,
            provider=LLMProvider.CLAUDE,
            command=command,
            response_text="",
            stderr="",
            error_message=error_text,
            exit_code=1,
        )

    response_text = "\n".join(final_text).strip()
    if not response_text and result_msg is not None:
        raw_result = getattr(result_msg, "result", "")
        if isinstance(raw_result, str):
            response_text = raw_result.strip()

    return LLMCLIResult(
        ok=True,
        provider=LLMProvider.CLAUDE,
        command=command,
        response_text=response_text,
        stderr="",
        exit_code=0,
    )


def run_llm_structured_patch_non_interactive(
    *,
    provider: LLMProvider,
    prompt: str,
    timeout_seconds: int = 120,
    cwd: Path | None = None,
    model: str | None = None,
) -> LLMStructuredPatchResult:
    """Run LLM CLI non-interactively and parse structured patch response."""
    cli_result = run_llm_cli_non_interactive(
        provider=provider,
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        cwd=cwd,
        model=model,
    )
    if not cli_result.ok:
        return LLMStructuredPatchResult(
            ok=False,
            provider=provider,
            cli_result=cli_result,
            parse_error="CLI execution failed",
        )

    try:
        parsed = parse_structured_patch_response(cli_result.response_text)
    except ValueError as exc:
        return LLMStructuredPatchResult(
            ok=False,
            provider=provider,
            cli_result=cli_result,
            parse_error=str(exc),
        )

    return LLMStructuredPatchResult(
        ok=True,
        provider=provider,
        cli_result=cli_result,
        parsed=parsed,
    )


def _non_interactive_env() -> dict[str, str]:
    env = dict(os.environ)
    env["CI"] = "1"
    env["TERM"] = "dumb"
    env["NO_COLOR"] = "1"
    return env


def _safe_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _snapshot_tree_hashes(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(root).as_posix()
        with contextlib.suppress(OSError):
            snapshot[rel_path] = _hash_path(path)
    return snapshot


def _hash_path(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _collect_changed_paths(
    before: dict[str, str],
    after: dict[str, str],
) -> list[str]:
    changed: list[str] = []
    keys = sorted(set(before) | set(after))
    for key in keys:
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed


def _tail_text(
    text: str,
    *,
    max_chars: int = 5000,
    max_lines: int = 120,
) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    lines = normalized.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    tail = "\n".join(lines)
    if len(tail) > max_chars:
        tail = tail[-max_chars:]
    return tail.strip()


def _build_direct_edit_log(
    *,
    provider: LLMProvider,
    command: list[str],
    cwd: Path,
    exit_code: int,
    changed_rel_paths: list[str],
    stdout_tail: str,
    stderr_tail: str,
    error_message: str,
    attempts: int,
) -> str:
    lines = [
        f"Provider: {provider.value}",
        f"Attempt: {attempts}",
        f"Command: {' '.join(command)}",
        f"CWD: {cwd}",
        f"Exit Code: {exit_code}",
    ]
    if changed_rel_paths:
        lines.append(f"Changed Files ({len(changed_rel_paths)}):")
        lines.extend(f"- {path}" for path in changed_rel_paths)
    else:
        lines.append("Changed Files (0):")
    if error_message:
        lines.append(f"Error: {error_message}")
    if stdout_tail:
        lines.extend(["", "STDOUT (tail):", stdout_tail])
    if stderr_tail:
        lines.extend(["", "STDERR (tail):", stderr_tail])
    return "\n".join(lines).strip()

