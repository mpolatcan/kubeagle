"""Unit tests for helm renderer helper."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from kubeagle.optimizer import helm_renderer


def _create_local_chart(tmp_path: Path) -> tuple[Path, Path]:
    chart_dir = tmp_path / "demo-chart"
    chart_dir.mkdir(parents=True, exist_ok=True)
    (chart_dir / "Chart.yaml").write_text(
        "apiVersion: v2\nname: demo-chart\nversion: 0.1.0\n",
        encoding="utf-8",
    )
    values_file = chart_dir / "values.yaml"
    values_file.write_text("replicaCount: 1\n", encoding="utf-8")
    return chart_dir, values_file


def test_render_chart_success(monkeypatch, tmp_path: Path) -> None:
    """Render should parse YAML documents when helm succeeds."""
    chart_dir, values_file = _create_local_chart(tmp_path)
    rendered_yaml = (
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        "metadata:\n"
        "  name: demo\n"
        "spec:\n"
        "  template:\n"
        "    spec:\n"
        "      containers:\n"
        "        - name: app\n"
        "---\n"
        "[]\n"
    )

    def _fake_run(*args, **kwargs):
        _ = args, kwargs
        return SimpleNamespace(returncode=0, stdout=rendered_yaml, stderr="")

    monkeypatch.setattr(helm_renderer.subprocess, "run", _fake_run)

    result = helm_renderer.render_chart(
        chart_dir=chart_dir,
        values_file=values_file,
        release_name="demo",
    )

    assert result.ok is True
    assert result.error_kind == ""
    assert result.command[:2] == ["helm", "template"]
    assert len(result.docs) == 1
    assert result.docs[0]["kind"] == "Deployment"


def test_render_chart_render_failed(monkeypatch, tmp_path: Path) -> None:
    """Render should expose stderr when helm returns non-zero exit code."""
    chart_dir, values_file = _create_local_chart(tmp_path)

    def _fake_run(*args, **kwargs):
        _ = args, kwargs
        return SimpleNamespace(returncode=1, stdout="", stderr="template error")

    monkeypatch.setattr(helm_renderer.subprocess, "run", _fake_run)

    result = helm_renderer.render_chart(
        chart_dir=chart_dir,
        values_file=values_file,
    )

    assert result.ok is False
    assert result.error_kind == "render_failed"
    assert "template error" in result.error_message


def test_render_chart_timeout(monkeypatch, tmp_path: Path) -> None:
    """Render should return timeout details when helm exceeds timeout."""
    chart_dir, values_file = _create_local_chart(tmp_path)

    def _fake_run(*args, **kwargs):
        _ = args, kwargs
        raise subprocess.TimeoutExpired(
            cmd=["helm", "template"],
            timeout=1,
            output=b"partial-output",
            stderr=b"timed out",
        )

    monkeypatch.setattr(helm_renderer.subprocess, "run", _fake_run)

    result = helm_renderer.render_chart(
        chart_dir=chart_dir,
        values_file=values_file,
        timeout_seconds=1,
    )

    assert result.ok is False
    assert result.error_kind == "timeout"
    assert result.stdout == "partial-output"
    assert result.stderr == "timed out"


def test_render_chart_helm_missing(monkeypatch, tmp_path: Path) -> None:
    """Render should surface missing helm binary cleanly."""
    chart_dir, values_file = _create_local_chart(tmp_path)

    def _fake_run(*args, **kwargs):
        _ = args, kwargs
        raise FileNotFoundError("helm not found")

    monkeypatch.setattr(helm_renderer.subprocess, "run", _fake_run)

    result = helm_renderer.render_chart(
        chart_dir=chart_dir,
        values_file=values_file,
    )

    assert result.ok is False
    assert result.error_kind == "helm_missing"
    assert "helm not found" in result.error_message


def test_render_chart_retries_with_parent_chart_only_render(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Missing dependencies should trigger parent-only render retry."""
    chart_dir, values_file = _create_local_chart(tmp_path)
    seen_commands: list[list[str]] = []
    rendered_yaml = (
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        "metadata:\n"
        "  name: demo\n"
        "spec:\n"
        "  template:\n"
        "    spec:\n"
        "      containers:\n"
        "        - name: app\n"
    )

    def _fake_run(command, *args, **kwargs):
        _ = args, kwargs
        seen_commands.append(list(command))
        if command[:2] == ["helm", "dependency"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if len(seen_commands) == 1:
            return SimpleNamespace(
                returncode=1,
                stdout="",
                stderr=(
                    "Error: An error occurred while checking for chart dependencies. "
                    "found in Chart.yaml, but missing in charts/ directory"
                ),
            )
        return SimpleNamespace(returncode=0, stdout=rendered_yaml, stderr="")

    monkeypatch.setattr(helm_renderer.subprocess, "run", _fake_run)

    result = helm_renderer.render_chart(
        chart_dir=chart_dir,
        values_file=values_file,
        release_name="demo",
    )

    assert result.ok is True
    assert result.parent_only_render_attempted is True
    assert not any(cmd[:3] == ["helm", "dependency", "build"] for cmd in seen_commands)


def test_render_chart_parent_only_render_failure(monkeypatch, tmp_path: Path) -> None:
    """Retry should return parent_render_failed when parent-only render still fails."""
    chart_dir, values_file = _create_local_chart(tmp_path)
    call_count = {"template": 0}

    def _fake_run(command, *args, **kwargs):
        _ = args, kwargs
        if command[:2] == ["helm", "template"]:
            call_count["template"] += 1
            if call_count["template"] == 1:
                return SimpleNamespace(
                    returncode=1,
                    stdout="",
                    stderr=(
                        "Error: An error occurred while checking for chart dependencies. "
                        "found in Chart.yaml, but missing in charts/ directory"
                    ),
                )
            return SimpleNamespace(returncode=1, stdout="", stderr="invalid template")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(helm_renderer.subprocess, "run", _fake_run)

    result = helm_renderer.render_chart(
        chart_dir=chart_dir,
        values_file=values_file,
    )

    assert result.ok is False
    assert result.error_kind == "parent_render_failed"
    assert result.parent_only_render_attempted is True
    assert "invalid template" in result.error_message
