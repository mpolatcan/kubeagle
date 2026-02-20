"""Unit tests for rendered manifest to rule-input mapping."""

from __future__ import annotations

from typing import Any

from kubeagle.optimizer.rendered_rule_input import (
    build_rule_inputs_from_rendered,
)


def _deployment_doc() -> dict[str, Any]:
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "payments"},
        "spec": {
            "replicas": 3,
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "app",
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "200m", "memory": "256Mi"},
                            },
                            "livenessProbe": {"httpGet": {"path": "/healthz", "port": 8080}},
                            "readinessProbe": {"httpGet": {"path": "/readyz", "port": 8080}},
                            "startupProbe": {"httpGet": {"path": "/startz", "port": 8080}},
                            "securityContext": {"runAsUser": 1000, "runAsNonRoot": True},
                        }
                    ],
                    "affinity": {
                        "podAntiAffinity": {
                            "preferredDuringSchedulingIgnoredDuringExecution": [
                                {"weight": 100}
                            ]
                        }
                    },
                    "topologySpreadConstraints": [
                        {
                            "maxSkew": 1,
                            "topologyKey": "kubernetes.io/hostname",
                            "whenUnsatisfiable": "ScheduleAnyway",
                        }
                    ],
                }
            },
        },
    }


def _hpa_doc(
    *,
    target_kind: str = "Deployment",
    target_name: str = "payments",
    min_replicas: int = 2,
) -> dict[str, Any]:
    return {
        "apiVersion": "autoscaling/v2",
        "kind": "HorizontalPodAutoscaler",
        "metadata": {"name": f"{target_name}-hpa"},
        "spec": {
            "scaleTargetRef": {"apiVersion": "apps/v1", "kind": target_kind, "name": target_name},
            "minReplicas": min_replicas,
            "maxReplicas": 5,
        },
    }


def test_build_rule_inputs_maps_resources_probes_availability_and_security() -> None:
    """Deployment + PDB should map all fields required by optimizer rules."""
    docs = [
        _deployment_doc(),
        {
            "apiVersion": "policy/v1",
            "kind": "PodDisruptionBudget",
            "metadata": {"name": "payments-pdb"},
            "spec": {"maxUnavailable": 1},
        },
    ]

    mapped = build_rule_inputs_from_rendered(docs, chart_name="payments")

    assert len(mapped) == 1
    item = mapped[0]
    assert item["chart_name"] == "payments"
    assert item["qos_class"] == "Burstable"
    assert item["resources"]["requests"]["cpu"] == "100m"
    assert item["resources"]["limits"]["memory"] == "256Mi"
    assert "livenessProbe" in item
    assert "readinessProbe" in item
    assert "startupProbe" in item
    assert item["replicas"] == 3
    assert item["has_anti_affinity"] is True
    assert len(item["topologySpreadConstraints"]) == 1
    assert item["securityContext"]["runAsUser"] == 1000
    assert item["podDisruptionBudget"]["enabled"] is True
    assert item["podDisruptionBudget"]["maxUnavailable"] == 1


def test_build_rule_inputs_maps_cronjob_parallelism() -> None:
    """CronJob should map nested pod spec and parallelism as replicas input."""
    docs = [
        {
            "apiVersion": "batch/v1",
            "kind": "CronJob",
            "metadata": {"name": "billing-job"},
            "spec": {
                "jobTemplate": {
                    "spec": {
                        "parallelism": 2,
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "worker",
                                        "resources": {
                                            "requests": {
                                                "cpu": "50m",
                                                "memory": "64Mi",
                                            },
                                            "limits": {
                                                "cpu": "100m",
                                                "memory": "128Mi",
                                            },
                                        },
                                    }
                                ]
                            }
                        },
                    }
                }
            },
        }
    ]

    mapped = build_rule_inputs_from_rendered(docs, chart_name="billing")

    assert len(mapped) == 1
    assert mapped[0]["replicas"] == 2
    assert mapped[0]["qos_class"] == "Burstable"
    assert mapped[0]["resources"]["requests"]["cpu"] == "50m"


def test_build_rule_inputs_uses_hpa_min_replicas_when_deployment_replicas_missing() -> None:
    """Deployment without spec.replicas should use matching HPA minReplicas."""
    deployment = _deployment_doc()
    deployment["spec"].pop("replicas", None)

    docs = [deployment, _hpa_doc()]

    mapped = build_rule_inputs_from_rendered(docs, chart_name="payments")

    assert len(mapped) == 1
    assert mapped[0]["replicas"] == 2


def test_build_rule_inputs_deduplicates_same_workload_identity() -> None:
    """Duplicate workload docs with same identity should keep the richer probe config."""
    rich = _deployment_doc()
    sparse = _deployment_doc()
    sparse["spec"].pop("replicas", None)
    containers = sparse["spec"]["template"]["spec"]["containers"]
    container = containers[0]
    container.pop("livenessProbe", None)
    container.pop("readinessProbe", None)
    container.pop("startupProbe", None)

    docs = [sparse, rich]

    mapped = build_rule_inputs_from_rendered(docs, chart_name="payments")

    assert len(mapped) == 1
    item = mapped[0]
    assert item["replicas"] == 3
    assert "livenessProbe" in item
    assert "readinessProbe" in item
    assert "startupProbe" in item


def test_build_rule_inputs_ignores_non_workload_docs() -> None:
    """Service/ConfigMap docs should not be converted to rule inputs."""
    docs = [
        {"apiVersion": "v1", "kind": "Service", "metadata": {"name": "svc"}},
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "cfg"}},
    ]

    mapped = build_rule_inputs_from_rendered(docs, chart_name="noop")

    assert mapped == []


def test_build_rule_inputs_best_effort_when_resources_missing() -> None:
    """Workloads without any requests/limits should be mapped as BestEffort."""
    docs = [
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "best-effort"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "app",
                            }
                        ]
                    }
                }
            },
        }
    ]

    mapped = build_rule_inputs_from_rendered(docs, chart_name="best-effort")

    assert len(mapped) == 1
    assert mapped[0]["qos_class"] == "BestEffort"
