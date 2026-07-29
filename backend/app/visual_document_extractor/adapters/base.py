from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import ValidationError

from ..execution import IsolatedExecutionError, ProcessLimits, execute_isolated
from ..models import (
    AdapterCapability,
    AdapterResult,
    AttemptStatus,
    ExtractionAttempt,
    PageClassification,
    PageInput,
)


class AdapterRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    VISION = "vision"


class AdapterExecutionError(Exception):
    """Provider-neutral adapter error safe to cross the contract boundary."""

    def __init__(
        self,
        code: str,
        safe_message: str,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.retryable = retryable


@runtime_checkable
class ExtractionAdapter(Protocol):
    name: str
    version: str
    technology: str
    role: AdapterRole
    classifications: Sequence[PageClassification]

    def probe(self) -> AdapterCapability: ...

    def extract(self, page: PageInput) -> AdapterResult: ...


AdapterExecutor = Callable[[PageInput], AdapterResult]


class OptionalDependencyAdapter:
    """Lazy, provider-neutral boundary for an optional parser integration.

    Merely constructing or probing this adapter never imports the heavyweight
    parser. Production integration supplies an executor that performs the
    provider-specific conversion into ``AdapterResult``.
    """

    name = "optional"
    technology = "optional"
    role = AdapterRole.PRIMARY
    dependency_modules: tuple[str, ...] = ()
    dependency_distribution: str | None = None
    classifications: Sequence[PageClassification] = tuple(PageClassification)

    def __init__(
        self,
        *,
        executor: AdapterExecutor | None = None,
        version: str | None = None,
        process_limits: ProcessLimits | None = None,
    ) -> None:
        self._executor = executor
        self._process_limits = process_limits
        self.version = version or self._installed_version() or "unconfigured"

    def _installed_version(self) -> str | None:
        if not self.dependency_distribution:
            return None
        try:
            return importlib.metadata.version(self.dependency_distribution)
        except importlib.metadata.PackageNotFoundError:
            return None

    def _missing_dependencies(self) -> list[str]:
        missing: list[str] = []
        for module in self.dependency_modules:
            try:
                spec = importlib.util.find_spec(module)
            except (ImportError, ModuleNotFoundError, ValueError):
                spec = None
            if spec is None:
                missing.append(module)
        return missing

    def probe(self) -> AdapterCapability:
        if self._executor is not None:
            return AdapterCapability(
                name=self.name,
                version=self.version,
                available=True,
                classifications=list(self.classifications),
            )

        missing = self._missing_dependencies()
        if missing:
            reason = "Optional dependency not installed: " + ", ".join(missing)
        elif self.dependency_modules:
            reason = "Parser is installed but its adapter executor is not configured"
        else:
            reason = "Adapter executor is not configured"
        return AdapterCapability(
            name=self.name,
            version=self.version if self.version != "unconfigured" else None,
            available=False,
            reason=reason,
            classifications=list(self.classifications),
        )

    def extract(self, page: PageInput) -> AdapterResult:
        started_at = datetime.now(timezone.utc)
        capability = self.probe()
        if not capability.available or self._executor is None:
            return self._failure_result(
                status=AttemptStatus.UNAVAILABLE,
                code="adapter_unavailable",
                message=capability.reason or "Adapter is unavailable",
                retryable=False,
                started_at=started_at,
            )

        try:
            raw_result = execute_isolated(
                self._executor, page, limits=self._process_limits
            )
            try:
                result = AdapterResult.model_validate(raw_result)
            except ValidationError:
                return self._failure_result(
                    status=AttemptStatus.FAILED,
                    code="invalid_adapter_output",
                    message="Adapter returned output that does not match the contract",
                    retryable=False,
                    started_at=started_at,
                )
            return self._normalize_result(result, started_at=started_at)
        except IsolatedExecutionError as exc:
            status = (
                AttemptStatus.TIMEOUT
                if exc.code in {"adapter_timeout", "adapter_capacity_timeout"}
                else AttemptStatus.FAILED
            )
            return self._failure_result(
                status=status,
                code=exc.code,
                message=exc.safe_message,
                retryable=exc.retryable,
                started_at=started_at,
            )
        except AdapterExecutionError as exc:
            return self._failure_result(
                status=AttemptStatus.FAILED,
                code=exc.code,
                message=exc.safe_message,
                retryable=exc.retryable,
                started_at=started_at,
            )
        except Exception:
            # Provider exceptions can include source content or credentials.
            return self._failure_result(
                status=AttemptStatus.FAILED,
                code="adapter_execution_failed",
                message="Adapter execution failed",
                retryable=False,
                started_at=started_at,
            )

    def _normalize_result(
        self,
        result: AdapterResult,
        *,
        started_at: datetime,
    ) -> AdapterResult:
        completed_at = datetime.now(timezone.utc)
        attempt = result.attempt.model_copy(
            update={
                "parser": self.name,
                "version": self.version,
                "started_at": started_at,
                "completed_at": completed_at,
            }
        )
        return result.model_copy(update={"attempt": attempt})

    def _failure_result(
        self,
        *,
        status: AttemptStatus,
        code: str,
        message: str,
        retryable: bool,
        started_at: datetime,
    ) -> AdapterResult:
        return AdapterResult(
            attempt=ExtractionAttempt(
                parser=self.name,
                version=self.version,
                status=status,
                error_code=code,
                error_message=message,
                retryable=retryable,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
        )
