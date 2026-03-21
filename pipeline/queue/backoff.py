"""指數退避計算模組。"""
import random


def calculate_backoff(
    retry_count: int,
    base_delay: float = 5.0,
    max_delay: float = 300.0,
    jitter: bool = True,
) -> float:
    """計算指數退避延遲秒數。"""
    delay = min(base_delay * (2 ** retry_count), max_delay)
    if jitter:
        delay += random.uniform(0, delay * 0.1)
    return delay


def should_retry(retry_count: int, max_retries: int) -> bool:
    """判斷是否應該重試。"""
    return retry_count < max_retries
