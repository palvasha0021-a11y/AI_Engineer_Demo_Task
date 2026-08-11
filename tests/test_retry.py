import pytest
import asyncio
from src.llm.retry import execute_with_retry


@pytest.mark.asyncio
async def test_execute_with_retry_success():
    attempts = 0

    async def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise Exception("429 Too Many Requests")
        return "Success"

    result = await execute_with_retry(flaky_func, max_retries=3, backoff_factor=0.01)
    assert result == "Success"
    assert attempts == 2


@pytest.mark.asyncio
async def test_execute_with_retry_failure_exhaustion():
    async def always_failing_func():
        raise Exception("500 Internal Server Error")

    with pytest.raises(Exception) as exc_info:
        await execute_with_retry(always_failing_func, max_retries=2, backoff_factor=0.01)

    assert "500 Internal Server Error" in str(exc_info.value)
