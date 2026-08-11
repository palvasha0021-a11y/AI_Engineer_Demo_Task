import asyncio
import random
import time
from typing import Callable, Any, Optional
from src.utils.logger import logger


async def execute_with_retry(
    coro_func: Callable[[], Any],
    max_retries: int = 3,
    backoff_factor: float = 1.5,
    provider_name: str = "LLMProvider"
) -> Any:
    """Execute an async function with exponential backoff, jitter, and 429 Retry-After support."""
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            return await coro_func()
        except Exception as exc:
            last_exception = exc
            err_msg = str(exc)
            
            # Check for 429 rate limit or 5xx server errors
            is_rate_limit = "429" in err_msg or "rate limit" in err_msg.lower() or "quota" in err_msg.lower()

            if attempt == max_retries:
                logger.error(
                    f"Max retries reached for provider {provider_name}",
                    attempt=attempt,
                    error=err_msg
                )
                raise exc

            # Calculate delay with exponential backoff + jitter
            sleep_time = (backoff_factor ** attempt) + random.uniform(0.1, 0.5)

            # Extract Retry-After if available in exception message/attributes
            retry_after = getattr(exc, "retry_after", None)
            if retry_after and isinstance(retry_after, (int, float)):
                sleep_time = max(sleep_time, float(retry_after))

            logger.warning(
                f"Retry attempt {attempt}/{max_retries} for {provider_name}",
                error=err_msg,
                backoff_delay=round(sleep_time, 2),
                is_rate_limit=is_rate_limit
            )

            await asyncio.sleep(sleep_time)

    raise last_exception
