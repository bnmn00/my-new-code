"""Weibo scheduled crawler.

This script periodically fetches posts from specified Weibo users and saves
responses in their original JSON format.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import requests


logger = logging.getLogger(__name__)


class WeiboCrawler:
    """Crawler that downloads recent Weibo posts for a list of user IDs."""

    BASE_URL = "https://weibo.com/ajax/statuses/mymblog"

    def __init__(
        self,
        user_ids: Iterable[str],
        output_dir: Path | str = "data",
        session: Optional[requests.Session] = None,
        timeout: int = 15,
    ) -> None:
        self.user_ids = list(user_ids)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = session or requests.Session()
        self.timeout = timeout
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://weibo.com/",
            }
        )

    def _output_file_for(self, uid: str) -> Path:
        return self.output_dir / f"{uid}.jsonl"

    def _known_ids_file_for(self, uid: str) -> Path:
        return self.output_dir / f"{uid}_ids.json"

    def _load_known_ids(self, uid: str) -> Set[str]:
        path = self._known_ids_file_for(uid)
        if not path.exists():
            return set()
        try:
            with path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
                if isinstance(data, list):
                    return set(str(i) for i in data)
        except json.JSONDecodeError:
            logger.warning("Failed to parse IDs cache for %s, recreating it.", uid)
        return set()

    def _save_known_ids(self, uid: str, ids: Set[str]) -> None:
        path = self._known_ids_file_for(uid)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(sorted(ids), fp, ensure_ascii=False, indent=2)

    def fetch_user_posts(self, uid: str, page: int = 1) -> List[Dict]:
        params = {"uid": uid, "page": page}
        logger.debug("Fetching posts for %s page %s", uid, page)
        resp = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected response format: not a JSON object")
        data = payload.get("data")
        if isinstance(data, dict) and "list" in data:
            posts = data.get("list")
        else:
            posts = payload.get("list")
        if not isinstance(posts, list):
            raise ValueError("Unexpected response format: missing posts list")
        return posts

    def save_posts(self, uid: str, posts: List[Dict]) -> int:
        if not posts:
            return 0
        output_file = self._output_file_for(uid)
        known_ids = self._load_known_ids(uid)
        new_posts = []
        for post in posts:
            if not isinstance(post, dict):
                continue
            post_id = str(post.get("mid") or post.get("id") or post.get("mblogid"))
            if not post_id or post_id in known_ids:
                continue
            known_ids.add(post_id)
            post_copy = dict(post)
            post_copy.setdefault("_fetched_at", datetime.utcnow().isoformat())
            new_posts.append(post_copy)

        if not new_posts:
            return 0

        with output_file.open("a", encoding="utf-8") as fp:
            for post in new_posts:
                fp.write(json.dumps(post, ensure_ascii=False))
                fp.write("\n")
        self._save_known_ids(uid, known_ids)
        logger.info("Saved %d new posts for %s", len(new_posts), uid)
        return len(new_posts)

    def crawl_user(self, uid: str, max_pages: int = 1) -> int:
        total_saved = 0
        for page in range(1, max_pages + 1):
            try:
                posts = self.fetch_user_posts(uid, page=page)
            except requests.HTTPError as exc:
                logger.error("HTTP error fetching user %s page %s: %s", uid, page, exc)
                break
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Unexpected error fetching user %s page %s: %s", uid, page, exc)
                break
            saved = self.save_posts(uid, posts)
            total_saved += saved
            if not posts:
                break
        return total_saved

    def run_once(self) -> Dict[str, int]:
        results: Dict[str, int] = {}
        for uid in self.user_ids:
            saved = self.crawl_user(uid)
            results[uid] = saved
        return results


def run_scheduler(user_ids: Iterable[str], interval_seconds: int = 180) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    crawler = WeiboCrawler(user_ids)
    logger.info("Starting Weibo crawler for users: %s", ", ".join(user_ids))
    while True:
        start = time.monotonic()
        results = crawler.run_once()
        for uid, count in results.items():
            logger.info("Run saved %d new posts for %s", count, uid)
        elapsed = time.monotonic() - start
        sleep_time = max(0, interval_seconds - elapsed)
        if sleep_time:
            logger.info("Sleeping for %.1f seconds", sleep_time)
            time.sleep(sleep_time)


if __name__ == "__main__":
    USER_IDS = ["1767797335", "1344066980"]
    INTERVAL_SECONDS = 3 * 60
    run_scheduler(USER_IDS, INTERVAL_SECONDS)
