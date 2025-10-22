"""Implementation of the Weibo crawler that produced the QA failure."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Optional

import requests
from requests import Response, Session

from .config import CrawlerConfig
from .exceptions import (
    AuthenticationRequired,
    UnexpectedResponseFormat,
    WeiboCrawlerError,
)

LOGGER = logging.getLogger(__name__)


class WeiboCrawler:
    """Crawler responsible for collecting timeline posts from the mobile API."""

    def __init__(self, config: Optional[CrawlerConfig] = None, *, session: Optional[Session] = None) -> None:
        self._config = config or CrawlerConfig()
        self._session = session or requests.Session()
        if self._config.session_cookies:
            self._session.cookies.update(self._config.session_cookies)

    @property
    def config(self) -> CrawlerConfig:
        """Return the configuration in use by the crawler."""

        return self._config

    def _issue_request(self) -> Response:
        """Perform the HTTP request against the Weibo mobile API."""

        LOGGER.debug("Issuing request to %s with params=%s", self._config.base_url, self._config.build_params())
        response = self._session.get(
            self._config.base_url,
            headers=self._config.build_headers(),
            params=self._config.build_params(),
            timeout=self._config.timeout,
            verify=self._config.verify_tls,
        )
        LOGGER.debug("Received response with status=%s", response.status_code)
        response.raise_for_status()
        return response

    def _coerce_json(self, response: Response) -> Dict[str, Any]:
        """Convert the response payload to JSON and handle known failure cases."""

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:  # pragma: no cover - network failure scenario
            text = response.text[:2000]
            LOGGER.error("Failed to decode JSON payload: %s", text)
            raise UnexpectedResponseFormat("Response was not valid JSON") from exc

        if payload.get("ok") == 0 and payload.get("msg") == "timeout":  # pragma: no cover - API timeout case
            raise WeiboCrawlerError("The Weibo API reported a timeout")

        if payload.get("ok") == -100:
            raise AuthenticationRequired("Authentication required for the Weibo API request")

        return payload

    def _extract_cards(self, payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """Yield card entries embedded inside the API payload."""

        data = payload.get("data")
        if not isinstance(data, dict):
            LOGGER.error("Unexpected response format: missing data object")
            raise UnexpectedResponseFormat("Unexpected response format: missing data object")

        cards = data.get("cards")
        if not isinstance(cards, list):
            LOGGER.error("Unexpected response format: missing cards list")
            raise UnexpectedResponseFormat("Unexpected response format: missing cards list")

        for card in cards:
            if not isinstance(card, dict):
                LOGGER.debug("Skipping malformed card entry: %r", card)
                continue
            yield card

    def _extract_posts(self, cards: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize card entries into a list of Weibo posts."""

        posts: List[Dict[str, Any]] = []
        for card in cards:
            if card.get("card_type") != 9:
                LOGGER.debug("Skipping card with unexpected type: %s", card.get("card_type"))
                continue

            mblog = card.get("mblog")
            if not isinstance(mblog, dict):
                LOGGER.warning("Card is missing mblog payload: %r", card)
                continue

            posts.append(mblog)

        if not posts:
            LOGGER.error("Unexpected response format: missing posts list")
            raise UnexpectedResponseFormat("Unexpected response format: missing posts list")

        return posts

    def crawl(self) -> List[Dict[str, Any]]:
        """Fetch posts from the Weibo API and return a normalized list of entries."""

        response = self._issue_request()
        payload = self._coerce_json(response)
        cards = self._extract_cards(payload)
        posts = self._extract_posts(cards)
        LOGGER.info("Fetched %d Weibo posts", len(posts))
        return posts


__all__ = ["WeiboCrawler", "CrawlerConfig"]
