"""Pod fetcher for cluster controller - fetches pod and workload data from Kubernetes cluster."""

from __future__ import annotations

import json
import logging
from typing import Any

from kubeagle.constants.timeouts import CLUSTER_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class PodFetcher:
    """Fetches pod data from Kubernetes cluster."""

    _PODS_CHUNK_SIZE = 200
    _RETRY_REQUEST_TIMEOUT = "45s"
    _TIMEOUT_ERROR_TOKENS = (
        "timed out",
        "timeout",
        "deadline exceeded",
        "i/o timeout",
        "context deadline exceeded",
    )

    def __init__(self, run_kubectl_func: Any) -> None:
        """Initialize with kubectl runner function.

        Args:
            run_kubectl_func: Async function to run kubectl commands
        """
        self._run_kubectl = run_kubectl_func

    @classmethod
    def _is_timeout_error(cls, error: Exception) -> bool:
        """Return True when error indicates timeout-like failure."""
        message = str(error).lower()
        return any(token in message for token in cls._TIMEOUT_ERROR_TOKENS)

    def _build_pods_args(
        self,
        request_timeout: str,
        *,
        namespace: str | None = None,
        running_only: bool = False,
    ) -> tuple[str, ...]:
        """Build kubectl args for pod fetch query."""
        args: list[str] = ["get", "pods"]
        if namespace:
            args.extend(["-n", namespace])
        else:
            args.append("-A")
        args.extend(
            [
                "-o",
                "json",
                f"--chunk-size={self._PODS_CHUNK_SIZE}",
                f"--request-timeout={request_timeout}",
            ]
        )
        if running_only:
            args.append("--field-selector=status.phase=Running")
        return tuple(args)

    @staticmethod
    def _parse_pod_items(output: str) -> list[dict[str, Any]]:
        """Parse pod JSON payload into item list."""
        data = json.loads(output)
        return data.get("items", [])

    def _attempt_plan(self, timeout_arg: str) -> list[tuple[str, bool]]:
        """Build timeout/mode attempt plan for pod queries."""
        attempt_plan: list[tuple[str, bool]] = []
        base_attempts: tuple[tuple[str, bool], ...]
        if timeout_arg == CLUSTER_REQUEST_TIMEOUT:
            base_attempts = (
                (CLUSTER_REQUEST_TIMEOUT, False),
                (self._RETRY_REQUEST_TIMEOUT, True),
            )
        else:
            base_attempts = (
                (timeout_arg, False),
                (CLUSTER_REQUEST_TIMEOUT, False),
                (self._RETRY_REQUEST_TIMEOUT, True),
            )
        for timeout, running_only in base_attempts:
            if (timeout, running_only) not in attempt_plan:
                attempt_plan.append((timeout, running_only))
        return attempt_plan

    async def _fetch_pods_for_scope(
        self,
        *,
        namespace: str | None,
        request_timeout: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch pods for a scope (all namespaces or one namespace)."""
        timeout_arg = request_timeout or CLUSTER_REQUEST_TIMEOUT
        attempt_plan = self._attempt_plan(timeout_arg)

        last_error: Exception | None = None
        for attempt, (timeout, running_only) in enumerate(attempt_plan, start=1):
            try:
                output = await self._run_kubectl(
                    self._build_pods_args(
                        timeout,
                        namespace=namespace,
                        running_only=running_only,
                    )
                )
                if not output:
                    return []
                return self._parse_pod_items(output)
            except json.JSONDecodeError:
                logger.exception("Error parsing pods JSON")
                return []
            except Exception as exc:
                last_error = exc
                is_retryable = self._is_timeout_error(exc)
                has_next_attempt = attempt < len(attempt_plan)
                if is_retryable and has_next_attempt:
                    mode = "running-only" if running_only else "all-phases"
                    logger.warning(
                        "Pod fetch timed out (attempt %s/%s, timeout=%s, mode=%s, namespace=%s), retrying",
                        attempt,
                        len(attempt_plan),
                        timeout,
                        mode,
                        namespace or "all",
                    )
                    continue
                raise

        if last_error is not None:
            raise last_error
        return []

    async def fetch_pods(
        self, request_timeout: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all pods from the cluster."""
        return await self._fetch_pods_for_scope(
            namespace=None,
            request_timeout=request_timeout,
        )

    async def fetch_pods_for_namespace(
        self,
        namespace: str,
        request_timeout: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch pods for a single namespace."""
        if not namespace:
            return []
        return await self._fetch_pods_for_scope(
            namespace=namespace,
            request_timeout=request_timeout,
        )
