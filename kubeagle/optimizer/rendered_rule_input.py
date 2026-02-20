"""Convert rendered manifests to optimizer rule input payloads."""

from __future__ import annotations

from typing import Any

_WORKLOAD_KINDS = {
    "Deployment",
    "StatefulSet",
    "DaemonSet",
    "ReplicaSet",
    "ReplicationController",
    "Job",
    "CronJob",
}


def build_rule_inputs_from_rendered(
    docs: list[dict[str, Any]],
    *,
    chart_name: str,
) -> list[dict[str, Any]]:
    """Build one rule-input dict per rendered workload."""
    pdb = _extract_pdb(docs)
    hpa_min_replicas = _extract_hpa_min_replicas(docs)
    workload_inputs: list[dict[str, Any]] = []

    for doc, pod_spec in _iter_unique_workload_docs(docs):
        identity = _workload_identity(doc)
        hpa_replicas = (
            _resolve_hpa_min_replicas(identity, hpa_min_replicas)
            if identity is not None
            else None
        )
        rule_input = _build_rule_input(
            chart_name=chart_name,
            doc=doc,
            pod_spec=pod_spec,
            pdb=pdb,
            hpa_min_replicas=hpa_replicas,
        )
        workload_inputs.append(rule_input)

    return workload_inputs


def _build_rule_input(
    *,
    chart_name: str,
    doc: dict[str, Any],
    pod_spec: dict[str, Any],
    pdb: dict[str, Any] | None,
    hpa_min_replicas: int | None,
) -> dict[str, Any]:
    containers = pod_spec.get("containers")
    first_container = containers[0] if isinstance(containers, list) and containers else {}
    if not isinstance(first_container, dict):
        first_container = {}

    resources = first_container.get("resources")
    resources_dict = resources if isinstance(resources, dict) else {}
    requests = resources_dict.get("requests")
    limits = resources_dict.get("limits")
    requests_dict = requests if isinstance(requests, dict) else {}
    limits_dict = limits if isinstance(limits, dict) else {}
    request_cpu = _string_or_none(requests_dict.get("cpu"))
    request_memory = _string_or_none(requests_dict.get("memory"))
    limit_cpu = _string_or_none(limits_dict.get("cpu"))
    limit_memory = _string_or_none(limits_dict.get("memory"))

    rule_input: dict[str, Any] = {
        "chart_name": chart_name,
        "qos_class": _determine_qos_class(
            request_cpu=request_cpu,
            request_memory=request_memory,
            limit_cpu=limit_cpu,
            limit_memory=limit_memory,
        ),
        "resources": {
            "requests": {
                "cpu": request_cpu,
                "memory": request_memory,
            },
            "limits": {
                "cpu": limit_cpu,
                "memory": limit_memory,
            },
        },
        "replicas": _extract_replicas(doc, hpa_min_replicas=hpa_min_replicas),
        "has_anti_affinity": _has_anti_affinity(pod_spec),
        "topologySpreadConstraints": _topology_constraints(pod_spec),
        "securityContext": _extract_security_context(first_container, pod_spec),
    }

    if isinstance(first_container.get("livenessProbe"), dict):
        rule_input["livenessProbe"] = first_container.get("livenessProbe")
    if isinstance(first_container.get("readinessProbe"), dict):
        rule_input["readinessProbe"] = first_container.get("readinessProbe")
    if isinstance(first_container.get("startupProbe"), dict):
        rule_input["startupProbe"] = first_container.get("startupProbe")

    if pdb:
        rule_input["podDisruptionBudget"] = dict(pdb)

    return rule_input


def _iter_unique_workload_docs(
    docs: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    selected: dict[tuple[str, str, str], tuple[dict[str, Any], dict[str, Any], int]] = {}
    anonymous: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for doc in docs:
        kind = str(doc.get("kind", "") or "")
        if kind not in _WORKLOAD_KINDS:
            continue
        pod_spec = _extract_pod_spec(doc)
        if not isinstance(pod_spec, dict):
            continue

        identity = _workload_identity(doc)
        if identity is None:
            anonymous.append((doc, pod_spec))
            continue

        score = _workload_doc_score(doc, pod_spec)
        existing = selected.get(identity)
        if existing is None or score > existing[2]:
            selected[identity] = (doc, pod_spec, score)

    unique_docs = [(doc, pod_spec) for doc, pod_spec, _ in selected.values()]
    unique_docs.extend(anonymous)
    return unique_docs


def _workload_identity(doc: dict[str, Any]) -> tuple[str, str, str] | None:
    kind = str(doc.get("kind", "") or "").strip()
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict):
        return None
    name = str(metadata.get("name", "") or "").strip()
    if not kind or not name:
        return None
    namespace = str(metadata.get("namespace", "") or "").strip()
    return (kind, name, namespace)


def _workload_doc_score(doc: dict[str, Any], pod_spec: dict[str, Any]) -> int:
    score = 0
    containers = pod_spec.get("containers")
    first_container = containers[0] if isinstance(containers, list) and containers else {}
    if not isinstance(first_container, dict):
        first_container = {}

    if isinstance(first_container.get("livenessProbe"), dict):
        score += 4
    if isinstance(first_container.get("readinessProbe"), dict):
        score += 4
    if isinstance(first_container.get("startupProbe"), dict):
        score += 4

    spec = doc.get("spec")
    if isinstance(spec, dict):
        if isinstance(spec.get("replicas"), int):
            score += 2
        if doc.get("kind") == "CronJob":
            job_template = spec.get("jobTemplate")
            if isinstance(job_template, dict):
                job_spec = job_template.get("spec")
                if isinstance(job_spec, dict) and isinstance(job_spec.get("parallelism"), int):
                    score += 2

    resources = first_container.get("resources")
    if isinstance(resources, dict) and resources:
        score += 1

    return score


def _extract_hpa_min_replicas(docs: list[dict[str, Any]]) -> dict[tuple[str, str, str], int]:
    target_map: dict[tuple[str, str, str], int] = {}

    for doc in docs:
        if str(doc.get("kind", "") or "") != "HorizontalPodAutoscaler":
            continue
        spec = doc.get("spec")
        if not isinstance(spec, dict):
            continue
        min_replicas = spec.get("minReplicas")
        if not isinstance(min_replicas, int):
            continue

        target_ref = spec.get("scaleTargetRef")
        if not isinstance(target_ref, dict):
            continue
        target_kind = str(target_ref.get("kind", "") or "").strip()
        target_name = str(target_ref.get("name", "") or "").strip()
        if not target_kind or not target_name:
            continue

        metadata = doc.get("metadata")
        namespace = ""
        if isinstance(metadata, dict):
            namespace = str(metadata.get("namespace", "") or "").strip()

        key = (target_kind, target_name, namespace)
        existing = target_map.get(key)
        if existing is None or min_replicas > existing:
            target_map[key] = min_replicas

    return target_map


def _resolve_hpa_min_replicas(
    identity: tuple[str, str, str],
    hpa_min_replicas: dict[tuple[str, str, str], int],
) -> int | None:
    exact = hpa_min_replicas.get(identity)
    if exact is not None:
        return exact

    kind, name, namespace = identity
    if namespace:
        global_match = hpa_min_replicas.get((kind, name, ""))
        if global_match is not None:
            return global_match

    candidates = [
        replicas
        for (target_kind, target_name, _target_namespace), replicas in hpa_min_replicas.items()
        if target_kind == kind and target_name == name
    ]
    if not candidates:
        return None
    return max(candidates)


def _extract_replicas(doc: dict[str, Any], *, hpa_min_replicas: int | None) -> int:
    kind = str(doc.get("kind", "") or "")
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        return 1
    if kind == "CronJob":
        job_spec = spec.get("jobTemplate")
        if isinstance(job_spec, dict):
            nested_spec = job_spec.get("spec")
            if isinstance(nested_spec, dict):
                parallelism = nested_spec.get("parallelism")
                if isinstance(parallelism, int):
                    return parallelism
        return 1
    replicas = spec.get("replicas")
    if isinstance(replicas, int):
        return replicas
    if isinstance(hpa_min_replicas, int):
        return hpa_min_replicas
    return 1


def _extract_pod_spec(doc: dict[str, Any]) -> dict[str, Any] | None:
    kind = str(doc.get("kind", "") or "")
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        return None

    if kind == "CronJob":
        job_template = spec.get("jobTemplate")
        if not isinstance(job_template, dict):
            return None
        job_spec = job_template.get("spec")
        if not isinstance(job_spec, dict):
            return None
        pod_template = job_spec.get("template")
        if not isinstance(pod_template, dict):
            return None
        pod_spec = pod_template.get("spec")
        return pod_spec if isinstance(pod_spec, dict) else None

    if kind == "Job":
        template = spec.get("template")
        if not isinstance(template, dict):
            return None
        pod_spec = template.get("spec")
        return pod_spec if isinstance(pod_spec, dict) else None

    template = spec.get("template")
    if not isinstance(template, dict):
        return None
    pod_spec = template.get("spec")
    return pod_spec if isinstance(pod_spec, dict) else None


def _extract_pdb(docs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for doc in docs:
        if str(doc.get("kind", "") or "") != "PodDisruptionBudget":
            continue
        spec = doc.get("spec")
        if not isinstance(spec, dict):
            continue
        payload: dict[str, Any] = {
            "enabled": True,
        }
        if "minAvailable" in spec:
            payload["minAvailable"] = spec.get("minAvailable")
        if "maxUnavailable" in spec:
            payload["maxUnavailable"] = spec.get("maxUnavailable")
        return payload
    return None


def _extract_security_context(
    container: dict[str, Any],
    pod_spec: dict[str, Any],
) -> dict[str, Any]:
    # Container securityContext has stronger signal for runAsUser in most charts.
    container_ctx = container.get("securityContext")
    if isinstance(container_ctx, dict) and container_ctx:
        return dict(container_ctx)
    pod_ctx = pod_spec.get("securityContext")
    if isinstance(pod_ctx, dict) and pod_ctx:
        return dict(pod_ctx)
    return {}


def _has_anti_affinity(pod_spec: dict[str, Any]) -> bool:
    affinity = pod_spec.get("affinity")
    if not isinstance(affinity, dict):
        return False
    anti = affinity.get("podAntiAffinity")
    if not isinstance(anti, dict):
        return False
    return bool(
        anti.get("preferredDuringSchedulingIgnoredDuringExecution")
        or anti.get("requiredDuringSchedulingIgnoredDuringExecution")
    )


def _topology_constraints(pod_spec: dict[str, Any]) -> list[Any]:
    constraints = pod_spec.get("topologySpreadConstraints")
    return constraints if isinstance(constraints, list) else []


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _determine_qos_class(
    *,
    request_cpu: str | None,
    request_memory: str | None,
    limit_cpu: str | None,
    limit_memory: str | None,
) -> str:
    resources = (request_cpu, request_memory, limit_cpu, limit_memory)
    if all(value is None for value in resources):
        return "BestEffort"
    if (
        request_cpu is not None
        and request_memory is not None
        and limit_cpu is not None
        and limit_memory is not None
        and request_cpu == limit_cpu
        and request_memory == limit_memory
    ):
        return "Guaranteed"
    return "Burstable"
