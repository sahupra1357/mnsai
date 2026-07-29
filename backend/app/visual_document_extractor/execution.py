from __future__ import annotations

import base64
import json
import math
import multiprocessing
import os
import pickle
import signal
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Any

from pydantic import ValidationError

from .models import AdapterResult, PageInput


class IsolatedExecutionError(Exception):
    def __init__(self, code: str, safe_message: str, *, retryable: bool = False) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.retryable = retryable


@dataclass(frozen=True)
class ProcessLimits:
    max_concurrent: int = 2
    memory_bytes: int | None = None
    cpu_seconds: int | None = 120
    termination_grace_seconds: float = 0.5


_semaphores: dict[int, threading.BoundedSemaphore] = {}
_semaphores_lock = threading.Lock()


def _semaphore(size: int) -> threading.BoundedSemaphore:
    if size < 1:
        raise ValueError("max_concurrent must be at least one")
    with _semaphores_lock:
        return _semaphores.setdefault(size, threading.BoundedSemaphore(size))


def _apply_resource_limits(limits: ProcessLimits) -> None:
    try:
        import resource
    except ImportError:
        return
    # Darwin's RLIMIT_AS is not a reliable per-process memory boundary and may reject
    # even limits above the worker's resident set before the executor starts. Production
    # memory enforcement is supplied by the Linux worker/container boundary.
    if (
        limits.memory_bytes is not None
        and hasattr(resource, "RLIMIT_AS")
        and not sys.platform.startswith("darwin")
    ):
        resource.setrlimit(
            resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes)
        )
    if limits.cpu_seconds is not None and hasattr(resource, "RLIMIT_CPU"):
        cpu = max(1, limits.cpu_seconds)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))


def _worker(
    connection: Connection,
    page_json: str,
    executor: Callable[[PageInput], AdapterResult],
    limits: ProcessLimits,
) -> None:
    try:
        if hasattr(os, "setsid"):
            os.setsid()
        try:
            _apply_resource_limits(limits)
        except (OSError, ValueError):
            connection.send(
                {
                    "ok": False,
                    "code": "adapter_resource_limit",
                    "message": "Adapter resource limits could not be applied",
                    "retryable": False,
                }
            )
            return
        page_payload = json.loads(page_json)
        page_payload["content"] = base64.b64decode(page_payload["content_b64"])
        del page_payload["content_b64"]
        page = PageInput.model_validate(page_payload)
        result = AdapterResult.model_validate(executor(page))
        connection.send({"ok": True, "result": result.model_dump(mode="json")})
    except IsolatedExecutionError as exc:
        connection.send(
            {
                "ok": False,
                "code": exc.code,
                "message": exc.safe_message,
                "retryable": exc.retryable,
            }
        )
    except (MemoryError, OSError):
        connection.send(
            {
                "ok": False,
                "code": "adapter_resource_limit",
                "message": "Adapter exceeded an execution resource limit",
                "retryable": False,
            }
        )
    except ValidationError:
        connection.send(
            {
                "ok": False,
                "code": "invalid_adapter_output",
                "message": "Adapter returned output that does not match the contract",
                "retryable": False,
            }
        )
    except BaseException as exc:
        # Never return provider exceptions: they can contain document data or secrets.
        if all(
            hasattr(exc, attribute)
            for attribute in ("code", "safe_message", "retryable")
        ):
            safe_exc: Any = exc
            connection.send(
                {
                    "ok": False,
                    "code": str(safe_exc.code),
                    "message": str(safe_exc.safe_message),
                    "retryable": bool(safe_exc.retryable),
                }
            )
            return
        connection.send(
            {
                "ok": False,
                "code": "adapter_execution_failed",
                "message": "Adapter execution failed",
                "retryable": False,
            }
        )
    finally:
        connection.close()


def _terminate(process: multiprocessing.Process, grace: float) -> None:
    if not process.is_alive():
        process.join()
        return
    try:
        if process.pid is not None and hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        pass
    process.join(grace)
    if process.is_alive():
        try:
            if process.pid is not None and hasattr(os, "killpg"):
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
        process.join()


def execute_isolated(
    executor: Callable[[PageInput], AdapterResult],
    page: PageInput,
    *,
    limits: ProcessLimits | None = None,
) -> AdapterResult:
    limits = limits or ProcessLimits(
        cpu_seconds=max(1, math.ceil(page.timeout_seconds))
    )
    timeout = page.timeout_seconds
    gate = _semaphore(limits.max_concurrent)
    if not gate.acquire(timeout=timeout):
        raise IsolatedExecutionError(
            "adapter_capacity_timeout",
            "Adapter execution capacity was unavailable before the page timeout",
            retryable=True,
        )
    parent: Connection | None = None
    process: Any = None
    try:
        methods = multiprocessing.get_all_start_methods()
        if "fork" not in methods and "forkserver" not in methods:
            raise IsolatedExecutionError(
                "adapter_isolation_unavailable",
                "Killable parser process isolation is unavailable on this platform",
            )
        try:
            pickle.dumps(executor)
            start_method = (
                "forkserver"
                if sys.platform.startswith("linux") and "forkserver" in methods
                else "fork"
            )
        except (pickle.PickleError, TypeError, AttributeError):
            start_method = "fork"
        context: Any = multiprocessing.get_context(start_method)
        parent, child = context.Pipe(duplex=False)
        page_payload = page.model_dump(mode="json", exclude={"content"})
        page_payload["content_b64"] = base64.b64encode(page.content).decode("ascii")
        process = context.Process(
            target=_worker,
            args=(child, json.dumps(page_payload), executor, limits),
            daemon=False,
        )
        process.start()
        child.close()
        assert parent is not None
        if not parent.poll(timeout):
            _terminate(process, limits.termination_grace_seconds)
            raise IsolatedExecutionError(
                "adapter_timeout",
                "Adapter exceeded the configured page timeout",
                retryable=True,
            )
        try:
            payload: Any = parent.recv()
        except EOFError as exc:
            process.join()
            code = (
                "adapter_resource_limit"
                if limits.memory_bytes is not None
                or (process.exitcode is not None and process.exitcode < 0)
                else "adapter_execution_failed"
            )
            message = (
                "Adapter exceeded an execution resource limit"
                if code == "adapter_resource_limit"
                else "Adapter execution failed"
            )
            raise IsolatedExecutionError(code, message) from exc
        process.join(limits.termination_grace_seconds)
        if not isinstance(payload, dict):
            raise IsolatedExecutionError(
                "invalid_adapter_output",
                "Adapter returned output that does not match the contract",
            )
        if not payload.get("ok"):
            raise IsolatedExecutionError(
                str(payload.get("code", "adapter_execution_failed")),
                str(payload.get("message", "Adapter execution failed")),
                retryable=bool(payload.get("retryable", False)),
            )
        try:
            return AdapterResult.model_validate(payload["result"])
        except (KeyError, ValidationError) as exc:
            raise IsolatedExecutionError(
                "invalid_adapter_output",
                "Adapter returned output that does not match the contract",
            ) from exc
    finally:
        if process is not None and process.is_alive():
            _terminate(process, limits.termination_grace_seconds)
        if parent is not None:
            parent.close()
        gate.release()
