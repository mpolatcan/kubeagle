"""Top metrics fetcher for cluster controller.

Fetches real-time usage metrics from Kubernetes metrics API via:
- kubectl top node
- kubectl top pod -A
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from kubeagle.constants.timeouts import CLUSTER_REQUEST_TIMEOUT
from kubeagle.utils.resource_parser import memory_str_to_bytes, parse_cpu

logger = logging.getLogger(__name__)


class TopMetricsFetcher:
    """Fetches node and pod real usage metrics from `kubectl top`."""

    _RETRY_REQUEST_TIMEOUT = "45s"
    _TARGET_TOP_NODE_CHUNK_SIZE = 60
    _TARGET_TOP_POD_CHUNK_SIZE = 120
    _TIMEOUT_ERROR_TOKENS = (
        "timed out",
        "timeout",
        "deadline exceeded",
        "i/o timeout",
        "context deadline exceeded",
    )

    def __init__(self, run_kubectl_func: Any) -> None:
        self._run_kubectl = run_kubectl_func

    @classmethod
    def _is_timeout_error(cls, error: Exception) -> bool:
        message = str(error).lower()
        return any(token in message for token in cls._TIMEOUT_ERROR_TOKENS)

    @staticmethod
    def _parse_cpu_mcores(cpu_value: str) -> float:
        return parse_cpu(str(cpu_value or "").strip()) * 1000.0

    @staticmethod
    def _parse_memory_bytes(memory_value: str) -> float:
        return memory_str_to_bytes(str(memory_value or "").strip())

    @staticmethod
    def _build_top_node_args(request_timeout: str) -> tuple[str, ...]:
        return (
            "top",
            "node",
            "--no-headers",
            f"--request-timeout={request_timeout}",
        )

    @staticmethod
    def _build_top_node_name_args(
        request_timeout: str,
        node_name: str,
    ) -> tuple[str, ...]:
        return (
            "top",
            "node",
            node_name,
            "--no-headers",
            f"--request-timeout={request_timeout}",
        )

    @staticmethod
    def _build_top_pod_args(request_timeout: str) -> tuple[str, ...]:
        return (
            "top",
            "pod",
            "-A",
            "--no-headers",
            f"--request-timeout={request_timeout}",
        )

    @staticmethod
    def _build_top_pod_name_args(
        request_timeout: str,
        namespace: str,
        pod_name: str,
    ) -> tuple[str, ...]:
        return (
            "top",
            "pod",
            "-n",
            namespace,
            pod_name,
            "--no-headers",
            f"--request-timeout={request_timeout}",
        )

    @staticmethod
    def _clean_names(values: list[str]) -> list[str]:
        ordered_unique: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = str(value or "").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered_unique.append(normalized)
        return ordered_unique

    @staticmethod
    def _chunk_names(values: list[str], chunk_size: int) -> list[list[str]]:
        if not values:
            return []
        return [values[i : i + chunk_size] for i in range(0, len(values), chunk_size)]

    async def _run_with_timeout_retry(
        self,
        args_builder: Any,
        request_timeout: str | None = None,
    ) -> str:
        timeout_arg = request_timeout or CLUSTER_REQUEST_TIMEOUT
        candidate_timeouts = (
            timeout_arg,
            CLUSTER_REQUEST_TIMEOUT,
            self._RETRY_REQUEST_TIMEOUT,
        )
        attempts: list[str] = []
        for timeout in candidate_timeouts:
            if timeout not in attempts:
                attempts.append(timeout)

        last_error: Exception | None = None
        for attempt_index, timeout in enumerate(attempts, start=1):
            args = args_builder(timeout)
            try:
                return await self._run_kubectl(args)
            except Exception as exc:
                last_error = exc
                if (
                    self._is_timeout_error(exc)
                    and attempt_index < len(attempts)
                ):
                    logger.warning(
                        "kubectl top timed out (attempt %s/%s with %s), retrying",
                        attempt_index,
                        len(attempts),
                        timeout,
                    )
                    continue
                raise

        if last_error is not None:
            raise last_error
        return ""

    def _parse_top_node_lines(self, output: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            # Expected shape: NAME CPU(cores) CPU% MEMORY(bytes) MEMORY%
            # Some kubectl versions can omit percentages; keep parsing defensive.
            node_name = str(parts[0]).strip()
            cpu_token = str(parts[1]).strip()
            memory_token = ""
            for token in parts[2:]:
                if not token.endswith("%"):
                    memory_token = token
                    break
            if not node_name or not cpu_token or not memory_token:
                continue
            rows.append(
                {
                    "node_name": node_name,
                    "cpu_mcores": self._parse_cpu_mcores(cpu_token),
                    "memory_bytes": self._parse_memory_bytes(memory_token),
                }
            )
        return rows

    def _parse_top_pod_lines(self, output: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            # Expected shape: NAMESPACE NAME CPU(cores) MEMORY(bytes)
            namespace = str(parts[0]).strip()
            pod_name = str(parts[1]).strip()
            cpu_token = str(parts[2]).strip()
            memory_token = str(parts[3]).strip()
            if not namespace or not pod_name:
                continue
            rows.append(
                {
                    "namespace": namespace,
                    "pod_name": pod_name,
                    "cpu_mcores": self._parse_cpu_mcores(cpu_token),
                    "memory_bytes": self._parse_memory_bytes(memory_token),
                }
            )
        return rows

    def _parse_top_pod_namespace_lines(
        self,
        output: str,
        namespace: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        effective_namespace = str(namespace or "").strip()
        if not effective_namespace:
            return rows
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            # Expected shape for namespace-scoped top:
            # NAME CPU(cores) MEMORY(bytes)
            pod_name = str(parts[0]).strip()
            cpu_token = str(parts[1]).strip()
            memory_token = str(parts[2]).strip()
            if not pod_name:
                continue
            rows.append(
                {
                    "namespace": effective_namespace,
                    "pod_name": pod_name,
                    "cpu_mcores": self._parse_cpu_mcores(cpu_token),
                    "memory_bytes": self._parse_memory_bytes(memory_token),
                }
            )
        return rows

    async def fetch_top_nodes(
        self,
        request_timeout: str | None = None,
    ) -> list[dict[str, Any]]:
        output = await self._run_with_timeout_retry(
            self._build_top_node_args,
            request_timeout=request_timeout,
        )
        if not output:
            return []
        return self._parse_top_node_lines(output)

    async def fetch_top_pods_all_namespaces(
        self,
        request_timeout: str | None = None,
    ) -> list[dict[str, Any]]:
        output = await self._run_with_timeout_retry(
            self._build_top_pod_args,
            request_timeout=request_timeout,
        )
        if not output:
            return []
        return self._parse_top_pod_lines(output)

    async def fetch_top_nodes_for_names(
        self,
        node_names: list[str],
        request_timeout: str | None = None,
    ) -> list[dict[str, Any]]:
        names = self._clean_names(node_names)
        if not names:
            return []

        async def _fetch_single_node(node_name: str) -> list[dict[str, Any]]:
            output = await self._run_with_timeout_retry(
                lambda timeout, single_name=node_name: self._build_top_node_name_args(
                    timeout,
                    single_name,
                ),
                request_timeout=request_timeout,
            )
            if not output:
                return []
            parsed_rows = self._parse_top_node_lines(output)
            return [
                row
                for row in parsed_rows
                if str(row.get("node_name", "") or "").strip() == node_name
            ]

        rows_by_node_name: dict[str, dict[str, Any]] = {}
        for chunk in self._chunk_names(names, self._TARGET_TOP_NODE_CHUNK_SIZE):
            results = await asyncio.gather(*[_fetch_single_node(node_name) for node_name in chunk])
            for rows in results:
                for row in rows:
                    node_name = str(row.get("node_name", "") or "").strip()
                    if not node_name:
                        continue
                    rows_by_node_name[node_name] = row
        return [rows_by_node_name[name] for name in names if name in rows_by_node_name]

    async def fetch_top_pods_for_namespace(
        self,
        namespace: str,
        pod_names: list[str],
        request_timeout: str | None = None,
    ) -> list[dict[str, Any]]:
        effective_namespace = str(namespace or "").strip()
        names = self._clean_names(pod_names)
        if not effective_namespace or not names:
            return []

        async def _fetch_single_pod(pod_name: str) -> list[dict[str, Any]]:
            output = await self._run_with_timeout_retry(
                lambda timeout, single_name=pod_name: self._build_top_pod_name_args(
                    timeout,
                    effective_namespace,
                    single_name,
                ),
                request_timeout=request_timeout,
            )
            if not output:
                return []
            parsed_rows = self._parse_top_pod_namespace_lines(output, effective_namespace)
            return [
                row
                for row in parsed_rows
                if str(row.get("pod_name", "") or "").strip() == pod_name
            ]

        rows_by_pod_name: dict[str, dict[str, Any]] = {}
        for chunk in self._chunk_names(names, self._TARGET_TOP_POD_CHUNK_SIZE):
            results = await asyncio.gather(*[_fetch_single_pod(pod_name) for pod_name in chunk])
            for rows in results:
                for row in rows:
                    pod_name = str(row.get("pod_name", "") or "").strip()
                    if not pod_name:
                        continue
                    rows_by_pod_name[pod_name] = row
        return [rows_by_pod_name[name] for name in names if name in rows_by_pod_name]
