"""Unit tests for full fix applier utilities."""

from __future__ import annotations

from pathlib import Path

from kubeagle.optimizer.full_fix_applier import (
    apply_full_fix_bundle_atomic,
    apply_full_fix_bundle_via_staged_replace,
    apply_unified_diff_to_text,
    parse_template_patches_from_bundle_diff,
    parse_values_patch_yaml,
    promote_staged_workspace_atomic,
)
from kubeagle.optimizer.llm_patch_protocol import FullFixTemplatePatch


def _prepare_chart(tmp_path: Path) -> tuple[Path, Path, Path]:
    chart_dir = tmp_path / "chart"
    chart_dir.mkdir()
    (chart_dir / "Chart.yaml").write_text("apiVersion: v2\nname: demo\nversion: 0.1.0\n", encoding="utf-8")
    templates = chart_dir / "templates"
    templates.mkdir()
    deployment = templates / "deployment.yaml"
    deployment.write_text(
        "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: demo\n",
        encoding="utf-8",
    )
    values = chart_dir / "values.yaml"
    values.write_text("replicaCount: 1\n", encoding="utf-8")
    return chart_dir, values, deployment


def test_parse_values_patch_yaml_requires_mapping() -> None:
    """Values patch YAML parser should enforce mapping root."""
    parsed = parse_values_patch_yaml("replicaCount: 2\n")
    assert parsed["replicaCount"] == 2


def test_parse_template_patches_from_bundle_diff() -> None:
    """Bundle diff parser should split multi-file unified diff."""
    diff_text = (
        "--- a/templates/deployment.yaml\n"
        "+++ b/templates/deployment.yaml\n"
        "@@ -1,1 +1,2 @@\n"
        " apiVersion: apps/v1\n"
        "+kind: Deployment\n"
        "\n"
        "--- a/templates/service.yaml\n"
        "+++ b/templates/service.yaml\n"
        "@@ -1,1 +1,1 @@\n"
        "-apiVersion: v1\n"
        "+apiVersion: v1\n"
    )
    patches = parse_template_patches_from_bundle_diff(
        diff_text=diff_text,
        allowed_files={"templates/deployment.yaml", "templates/service.yaml"},
    )
    assert len(patches) == 2
    assert patches[0].file == "templates/deployment.yaml"


def test_apply_unified_diff_to_text_success() -> None:
    """Single-file unified diff should apply with context matching."""
    original = "line1\nline2\n"
    diff = (
        "--- a/templates/deployment.yaml\n"
        "+++ b/templates/deployment.yaml\n"
        "@@ -1,2 +1,3 @@\n"
        " line1\n"
        "+line1_5\n"
        " line2\n"
    )
    updated = apply_unified_diff_to_text(original_text=original, unified_diff=diff)
    assert "line1_5" in updated


def test_apply_full_fix_bundle_atomic_success(tmp_path: Path) -> None:
    """Atomic bundle apply should update both template and values files."""
    chart_dir, values_path, deployment = _prepare_chart(tmp_path)
    patch = FullFixTemplatePatch(
        file="templates/deployment.yaml",
        purpose="add label",
        unified_diff=(
            "--- a/templates/deployment.yaml\n"
            "+++ b/templates/deployment.yaml\n"
            "@@ -1,4 +1,5 @@\n"
            " apiVersion: apps/v1\n"
            " kind: Deployment\n"
            " metadata:\n"
            "   name: demo\n"
            "+  labels:\n"
        ),
    )
    result = apply_full_fix_bundle_atomic(
        chart_dir=chart_dir,
        values_path=values_path,
        values_patch={"replicaCount": 2},
        template_patches=[patch],
    )
    assert result.ok is True
    assert "replicaCount: 2" in values_path.read_text(encoding="utf-8")
    assert "labels:" in deployment.read_text(encoding="utf-8")


def test_apply_full_fix_bundle_atomic_preserves_sequence_indentation(
    tmp_path: Path,
) -> None:
    """Atomic values patch should preserve existing YAML list indentation style."""
    chart_dir, values_path, _ = _prepare_chart(tmp_path)
    values_path.write_text(
        (
            "resources:\n"
            "    requests:\n"
            "      - name: cpu\n"
            '        value: "100m"\n'
        ),
        encoding="utf-8",
    )

    result = apply_full_fix_bundle_atomic(
        chart_dir=chart_dir,
        values_path=values_path,
        values_patch={"replicaCount": 2},
        template_patches=[],
    )

    assert result.ok is True
    updated = values_path.read_text(encoding="utf-8")
    assert "    requests:" in updated
    assert "      - name: cpu" in updated
    assert 'value: "100m"' in updated


def test_apply_full_fix_bundle_atomic_preserves_untouched_top_level_blocks(
    tmp_path: Path,
) -> None:
    """Atomic values patch should not reformat unrelated top-level sections."""
    chart_dir, values_path, _ = _prepare_chart(tmp_path)
    values_path.write_text(
        "replicaCount: 1\n"
        "\n"
        "image:\n"
        "    repository: sample/repo\n"
        "    pullPolicy: IfNotPresent\n"
        "\n"
        "resources:\n"
        "  requests:\n"
        '    cpu: "100m"\n',
        encoding="utf-8",
    )

    result = apply_full_fix_bundle_atomic(
        chart_dir=chart_dir,
        values_path=values_path,
        values_patch={"resources": {"requests": {"cpu": "200m"}}},
        template_patches=[],
    )

    assert result.ok is True
    updated = values_path.read_text(encoding="utf-8")
    assert (
        "image:\n"
        "    repository: sample/repo\n"
        "    pullPolicy: IfNotPresent\n"
    ) in updated
    assert 'cpu: "200m"' in updated


def test_apply_full_fix_bundle_atomic_preserves_nested_ingress_format_on_map_patch(
    tmp_path: Path,
) -> None:
    """Atomic apply should not normalize unrelated nested ingress formatting."""
    chart_dir, values_path, _ = _prepare_chart(tmp_path)
    values_path.write_text(
        "ingress:\n"
        "  enabled: true\n"
        '  className: "traefik"\n'
        "  annotations:\n"
        "    {}\n"
        "    # kubernetes.io/ingress.class: nginx\n"
        '    # kubernetes.io/tls-acme: "true"\n'
        "  hosts:\n"
        "    - host: old-host.example.com\n"
        "      paths:\n"
        "        - path: /\n"
        "          service: skeleton-websocket\n"
        "          servicePort: 4566\n"
        "  tls: []\n",
        encoding="utf-8",
    )

    result = apply_full_fix_bundle_atomic(
        chart_dir=chart_dir,
        values_path=values_path,
        values_patch={
            "ingress": {
                "enabled": True,
                "className": "traefik",
                "hosts": [
                    {
                        "host": "new-host.example.com",
                        "paths": [
                            {
                                "path": "/",
                                "service": "skeleton-websocket",
                                "servicePort": 4566,
                            }
                        ],
                    }
                ],
            }
        },
        template_patches=[],
    )

    assert result.ok is True
    updated = values_path.read_text(encoding="utf-8")
    assert "  enabled: true" in updated
    assert "  annotations:\n    {}" in updated
    assert "  tls: []" in updated
    assert "    - host: new-host.example.com" in updated
    assert "    enabled: true" not in updated


def test_apply_full_fix_bundle_atomic_skips_noop_nested_map_patch(
    tmp_path: Path,
) -> None:
    """No-op nested map payload should not rewrite YAML formatting."""
    chart_dir, values_path, _ = _prepare_chart(tmp_path)
    original = (
        "ingress:\n"
        "  enabled: true\n"
        '  className: "traefik"\n'
        "  annotations:\n"
        "    {}\n"
        "    # kubernetes.io/ingress.class: nginx\n"
        '    # kubernetes.io/tls-acme: "true"\n'
        "  hosts:\n"
        "    - host: skeleton-websocket.api.insidethekube.com\n"
        "      paths:\n"
        "        - path: /\n"
        "          service: skeleton-websocket\n"
        "          servicePort: 4566\n"
        "  tls: []\n"
    )
    values_path.write_text(original, encoding="utf-8")

    result = apply_full_fix_bundle_atomic(
        chart_dir=chart_dir,
        values_path=values_path,
        values_patch={
            "ingress": {
                "enabled": True,
                "className": "traefik",
                "hosts": [
                    {
                        "host": "skeleton-websocket.api.insidethekube.com",
                        "paths": [
                            {
                                "path": "/",
                                "service": "skeleton-websocket",
                                "servicePort": 4566,
                            }
                        ],
                    }
                ],
            }
        },
        template_patches=[],
    )

    assert result.ok is True
    assert values_path.read_text(encoding="utf-8") == original


def test_apply_full_fix_bundle_atomic_rolls_back_on_failure(tmp_path: Path) -> None:
    """Bundle apply should rollback when template patch fails."""
    chart_dir, values_path, deployment = _prepare_chart(tmp_path)
    original_values = values_path.read_text(encoding="utf-8")
    original_deploy = deployment.read_text(encoding="utf-8")
    bad_patch = FullFixTemplatePatch(
        file="templates/deployment.yaml",
        purpose="bad",
        unified_diff=(
            "--- a/templates/deployment.yaml\n"
            "+++ b/templates/deployment.yaml\n"
            "@@ -42,1 +42,1 @@\n"
            "-missing\n"
            "+new\n"
        ),
    )
    result = apply_full_fix_bundle_atomic(
        chart_dir=chart_dir,
        values_path=values_path,
        values_patch={"replicaCount": 3},
        template_patches=[bad_patch],
    )
    assert result.ok is False
    assert values_path.read_text(encoding="utf-8") == original_values
    assert deployment.read_text(encoding="utf-8") == original_deploy


def test_apply_full_fix_bundle_atomic_supports_updated_content(tmp_path: Path) -> None:
    """Atomic apply should accept full updated template content payloads."""
    chart_dir, values_path, deployment = _prepare_chart(tmp_path)
    patch = FullFixTemplatePatch(
        file="templates/deployment.yaml",
        purpose="replace template content",
        updated_content=(
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: demo\n"
            "spec:\n"
            "  replicas: 2\n"
        ),
    )
    result = apply_full_fix_bundle_atomic(
        chart_dir=chart_dir,
        values_path=values_path,
        values_patch={},
        template_patches=[patch],
    )
    assert result.ok is True
    assert "replicas: 2" in deployment.read_text(encoding="utf-8")


def test_apply_full_fix_bundle_via_staged_replace_success(tmp_path: Path) -> None:
    """Staged replace apply should update files without producing backups."""
    chart_dir, values_path, deployment = _prepare_chart(tmp_path)
    patch = FullFixTemplatePatch(
        file="templates/deployment.yaml",
        purpose="add label",
        unified_diff=(
            "--- a/templates/deployment.yaml\n"
            "+++ b/templates/deployment.yaml\n"
            "@@ -1,4 +1,5 @@\n"
            " apiVersion: apps/v1\n"
            " kind: Deployment\n"
            " metadata:\n"
            "   name: demo\n"
            "+  labels:\n"
        ),
    )
    result = apply_full_fix_bundle_via_staged_replace(
        chart_dir=chart_dir,
        values_path=values_path,
        values_patch={"replicaCount": 2},
        template_patches=[patch],
    )
    assert result.ok is True
    assert "replicaCount: 2" in values_path.read_text(encoding="utf-8")
    assert "labels:" in deployment.read_text(encoding="utf-8")


def test_apply_full_fix_bundle_via_staged_replace_noop(tmp_path: Path) -> None:
    """Staged replace apply should be no-op when no values/template changes are requested."""
    chart_dir, values_path, _ = _prepare_chart(tmp_path)
    original_values = values_path.read_text(encoding="utf-8")
    result = apply_full_fix_bundle_via_staged_replace(
        chart_dir=chart_dir,
        values_path=values_path,
        values_patch={},
        template_patches=[],
    )
    assert result.ok is True
    assert "No file changes requested" in result.note
    assert values_path.read_text(encoding="utf-8") == original_values


def test_promote_staged_workspace_atomic_success(tmp_path: Path) -> None:
    """Promote API should atomically copy staged files after hash guard checks."""
    chart_dir, values_path, deployment = _prepare_chart(tmp_path)
    staged_root = tmp_path / "staged"
    staged_chart = staged_root / "chart"
    staged_chart.mkdir(parents=True)
    (staged_chart / "Chart.yaml").write_text(
        (chart_dir / "Chart.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (staged_chart / "templates").mkdir()
    (staged_chart / "templates" / "deployment.yaml").write_text(
        deployment.read_text(encoding="utf-8") + "spec:\n  replicas: 2\n",
        encoding="utf-8",
    )
    (staged_chart / "values.yaml").write_text("replicaCount: 2\n", encoding="utf-8")

    import hashlib

    source_hashes = {
        "values.yaml": hashlib.sha256(values_path.read_bytes()).hexdigest(),
        "templates/deployment.yaml": hashlib.sha256(deployment.read_bytes()).hexdigest(),
    }
    result = promote_staged_workspace_atomic(
        chart_dir=chart_dir,
        staged_chart_dir=staged_chart,
        changed_rel_paths=["values.yaml", "templates/deployment.yaml"],
        source_hashes=source_hashes,
    )
    assert result.ok is True
    assert "replicaCount: 2" in values_path.read_text(encoding="utf-8")
    assert "replicas: 2" in deployment.read_text(encoding="utf-8")


def test_promote_staged_workspace_atomic_detects_hash_drift(tmp_path: Path) -> None:
    """Promote API should fail if source file changed since preview generation."""
    chart_dir, values_path, _ = _prepare_chart(tmp_path)
    staged_root = tmp_path / "staged"
    staged_chart = staged_root / "chart"
    staged_chart.mkdir(parents=True)
    (staged_chart / "Chart.yaml").write_text(
        (chart_dir / "Chart.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (staged_chart / "templates").mkdir()
    (staged_chart / "templates" / "deployment.yaml").write_text(
        (chart_dir / "templates" / "deployment.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (staged_chart / "values.yaml").write_text("replicaCount: 2\n", encoding="utf-8")

    values_path.write_text("replicaCount: 9\n", encoding="utf-8")
    result = promote_staged_workspace_atomic(
        chart_dir=chart_dir,
        staged_chart_dir=staged_chart,
        changed_rel_paths=["values.yaml"],
        source_hashes={"values.yaml": "stale-hash"},
    )
    assert result.ok is False
    assert "source file changed" in result.note.lower()
