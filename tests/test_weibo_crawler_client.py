import pathlib
import sys
import types
import unittest
from unittest.mock import Mock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Provide a lightweight stub for the requests module so the crawler can be imported
# in environments where the dependency is not installed.
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _SessionStub:
        def __init__(self):
            self.cookies = {}

        def get(self, *args, **kwargs):  # pragma: no cover - not used in tests
            raise NotImplementedError("Network access not implemented in stub")

    requests_stub.Session = _SessionStub
    requests_stub.Response = object

    sessions_stub = types.ModuleType("requests.sessions")
    sessions_stub.Session = _SessionStub

    sys.modules["requests"] = requests_stub
    sys.modules["requests.sessions"] = sessions_stub

from weibo_crawler.client import WeiboCrawler
from weibo_crawler.config import CrawlerConfig
from weibo_crawler.exceptions import AuthenticationRequired, UnexpectedResponseFormat


class WeiboCrawlerClientTests(unittest.TestCase):
    def _build_response(self, payload):
        response = Mock()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        response.status_code = 200
        return response

    def test_crawl_returns_posts(self):
        payload = {
            "ok": 1,
            "data": {
                "cards": [
                    {
                        "card_type": 9,
                        "mblog": {"id": "1", "text": "hello"},
                    }
                ]
            },
        }
        response = self._build_response(payload)
        session = Mock()
        session.get.return_value = response

        crawler = WeiboCrawler(config=CrawlerConfig(), session=session)

        posts = crawler.crawl()

        self.assertEqual(1, len(posts))
        self.assertEqual("1", posts[0]["id"])
        session.get.assert_called_once()
        response.json.assert_called_once()

    def test_crawl_raises_when_no_posts(self):
        payload = {
            "ok": 1,
            "data": {
                "cards": [
                    {
                        "card_type": 9,
                    }
                ]
            },
        }
        response = self._build_response(payload)
        session = Mock()
        session.get.return_value = response

        crawler = WeiboCrawler(config=CrawlerConfig(), session=session)

        with self.assertRaises(UnexpectedResponseFormat):
            crawler.crawl()

    def test_coerce_json_requires_authentication(self):
        payload = {
            "ok": -100,
        }
        response = self._build_response(payload)
        session = Mock()
        session.get.return_value = response

        crawler = WeiboCrawler(config=CrawlerConfig(), session=session)

        with self.assertRaises(AuthenticationRequired):
            crawler.crawl()


if __name__ == "__main__":
    unittest.main()
