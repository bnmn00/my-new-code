"""Configuration helpers for the Weibo crawler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class CrawlerConfig:
    """Runtime configuration for the Weibo crawler."""

    base_url: str = "https://m.weibo.cn/api/container/getIndex"
    container_id: str = "102803"
    page: int = 1
    session_cookies: Optional[Dict[str, str]] = field(default=None)
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/115.0 Safari/537.36"
    )
    timeout: float = 10.0
    verify_tls: bool = True

    def build_headers(self) -> Dict[str, str]:
        """Return HTTP headers to be used when issuing requests."""

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://m.weibo.cn/",
            "User-Agent": self.user_agent,
            "X-Requested-With": "XMLHttpRequest",
        }
        return headers

    def build_params(self) -> Dict[str, str]:
        """Return query parameters for the API request."""

        return {
            "containerid": self.container_id,
            "page": str(self.page),
        }
