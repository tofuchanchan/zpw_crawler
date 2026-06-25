from __future__ import annotations

import random
import time
from dataclasses import dataclass

import requests

from .config import DelayConfig


class FetchError(RuntimeError):
    def __init__(self, url: str, error_type: str, message: str, retry_count: int = 0):
        super().__init__(message)
        self.url = url
        self.error_type = error_type
        self.message = message
        self.retry_count = retry_count


@dataclass(slots=True)
class FetchResponse:
    url: str
    text: str
    status_code: int


class HttpFetcher:
    def __init__(
        self,
        *,
        timeout: int = 15,
        max_retries: int = 3,
        session: requests.Session | None = None,
        sleep_enabled: bool = True,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.sleep_enabled = sleep_enabled
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

    def fetch(self, url: str, delay: DelayConfig | None = None) -> FetchResponse:
        retry_count = 0
        last_error: FetchError | None = None

        while retry_count <= self.max_retries:
            if retry_count > 0 and self.sleep_enabled:
                time.sleep(min(30, 2**retry_count))

            try:
                response = self.session.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = FetchError(url, "request_error", str(exc), retry_count)
                retry_count += 1
                continue

            if response.status_code == 200:
                response.encoding = response.apparent_encoding or response.encoding or "utf-8"
                if delay and self.sleep_enabled:
                    time.sleep(random.uniform(delay.min, delay.max))
                return FetchResponse(url=response.url, text=response.text, status_code=response.status_code)

            if response.status_code in (401, 403):
                raise FetchError(url, "permission_denied", f"HTTP {response.status_code}", retry_count)
            if response.status_code == 404:
                raise FetchError(url, "not_found", "HTTP 404", retry_count)
            if response.status_code == 429:
                last_error = FetchError(url, "rate_limited", "HTTP 429", retry_count)
                retry_count += 1
                continue
            if 500 <= response.status_code < 600:
                last_error = FetchError(url, "server_error", f"HTTP {response.status_code}", retry_count)
                retry_count += 1
                continue

            raise FetchError(url, "http_error", f"HTTP {response.status_code}", retry_count)

        if last_error:
            raise last_error
        raise FetchError(url, "unknown_error", "请求失败", retry_count)
