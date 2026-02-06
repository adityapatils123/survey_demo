# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Retry utilities for robust error handling.
Provides decorators and functions for automatic retry logic with exponential backoff.
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Callable, Type, Tuple, Any, Optional

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 0.5
DEFAULT_MAX_DELAY = 30.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0


class RetryError(Exception):
    """Exception raised when all retry attempts are exhausted"""
    pass


def retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator for retrying function calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Tuple of exception types to catch and retry on
        on_retry: Optional callback function called on each retry (attempt_num, exception)
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        if on_retry:
                            try:
                                on_retry(attempt + 1, e)
                            except Exception:
                                pass  # Don't fail on retry callback errors
                        
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * backoff_multiplier, max_delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
            
            raise RetryError(
                f"{func.__name__} failed after {max_retries + 1} attempts"
            ) from last_exception
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        if on_retry:
                            try:
                                on_retry(attempt + 1, e)
                            except Exception:
                                pass  # Don't fail on retry callback errors
                        
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * backoff_multiplier, max_delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
            
            raise RetryError(
                f"{func.__name__} failed after {max_retries + 1} attempts"
            ) from last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def retry_async(
    func: Callable,
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> Any:
    """
    Retry an async function call with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Tuple of exception types to catch and retry on
        **kwargs: Keyword arguments for the function
    
    Returns:
        Result of the function call
    
    Raises:
        RetryError: If all retry attempts are exhausted
    """
    last_exception = None
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
                delay = min(delay * backoff_multiplier, max_delay)
            else:
                logger.error(
                    f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                )
    
    raise RetryError(
        f"{func.__name__} failed after {max_retries + 1} attempts"
    ) from last_exception


def retry_sync(
    func: Callable,
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> Any:
    """
    Retry a synchronous function call with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
        exceptions: Tuple of exception types to catch and retry on
        **kwargs: Keyword arguments for the function
    
    Returns:
        Result of the function call
    
    Raises:
        RetryError: If all retry attempts are exhausted
    """
    last_exception = None
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                time.sleep(delay)
                delay = min(delay * backoff_multiplier, max_delay)
            else:
                logger.error(
                    f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                )
    
    raise RetryError(
        f"{func.__name__} failed after {max_retries + 1} attempts"
    ) from last_exception
