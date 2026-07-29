from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path

import pytest

from app.visual_document_extractor.execution import (
    IsolatedExecutionError,
    ProcessLimits,
    execute_isolated,
)
from app.visual_document_extractor.models import (
    AdapterResult,
    AttemptStatus,
    ExtractionAttempt,
    PageClassification,
    PageInput,
)


def _page(timeout: float = 0.2) -> PageInput:
    return PageInput(
        document_id=uuid.uuid4(),
        page_number=1,
        media_type="image/png",
        content=b"content",
        classification=PageClassification.SCANNED,
        timeout_seconds=timeout,
    )


def _delayed_marker(page: PageInput) -> AdapterResult:
    marker = Path(page.content.decode())
    time.sleep(1)
    marker.write_text("worker survived", encoding="utf-8")
    return AdapterResult(
        attempt=ExtractionAttempt(
            parser="test", version="1", status=AttemptStatus.SUCCEEDED
        )
    )


def _burn_cpu(_page: PageInput) -> AdapterResult:
    while True:
        pass


def _exhaust_memory(_page: PageInput) -> AdapterResult:
    _ = bytearray(1024 * 1024 * 1024)
    return AdapterResult(
        attempt=ExtractionAttempt(
            parser="test", version="1", status=AttemptStatus.SUCCEEDED
        )
    )


@pytest.mark.skipif(os.name != "posix", reason="POSIX process isolation required")
def test_timeout_terminates_worker_instead_of_leaving_work_running(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "late-marker"
    page = _page()
    page.content = str(marker).encode()

    with pytest.raises(IsolatedExecutionError, match="page timeout") as error:
        execute_isolated(
            _delayed_marker,
            page,
            limits=ProcessLimits(memory_bytes=None, cpu_seconds=5),
        )

    assert error.value.code == "adapter_timeout"
    time.sleep(1.1)
    assert not marker.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX resource limits required")
def test_cpu_resource_limit_returns_safe_structured_error() -> None:
    with pytest.raises(IsolatedExecutionError) as error:
        execute_isolated(
            _burn_cpu,
            _page(timeout=3),
            limits=ProcessLimits(memory_bytes=None, cpu_seconds=1),
        )

    assert error.value.code == "adapter_resource_limit"
    assert "resource limit" in error.value.safe_message


@pytest.mark.skipif(
    os.name != "posix" or sys.platform.startswith("darwin"),
    reason="Linux RLIMIT_AS enforcement required",
)
def test_memory_resource_limit_returns_safe_structured_error() -> None:
    with pytest.raises(IsolatedExecutionError) as error:
        execute_isolated(
            _exhaust_memory,
            _page(timeout=3),
            limits=ProcessLimits(
                memory_bytes=256 * 1024 * 1024,
                cpu_seconds=2,
            ),
        )

    assert error.value.code == "adapter_resource_limit"
