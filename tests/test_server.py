import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from app import Handler
from provider import DataError


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        conn.request("GET", path, headers=headers or {})
        response = conn.getresponse()
        status, body, headers = response.status, response.read(), dict(response.getheaders())
        conn.close()
        return status, body, headers

    def test_only_public_assets_are_served(self):
        for path in ("/app.py", "/.git/config", "/.runtime/server.pid", "/../provider.py"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        status, body, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Stock Research Desk", body)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_other_hosts_and_origins_cannot_query_data(self):
        for headers in ({"Host": "attacker.example"}, {"Origin": "https://attacker.example"}):
            self.assertEqual(self.request("/api/status", headers)[0], 403)

    def test_bad_queries_rejected_without_reading_norgate(self):
        with patch("app.load_prices") as load:
            for query in ("", "symbols=AAPL", "symbols=AAPL&benchmark=SPY&start=2025-01-01&end=2025-02-01&extra=1", "symbols=AAPL&symbols=MSFT&benchmark=SPY&start=2025-01-01&end=2025-02-01"):
                self.assertEqual(self.request("/api/analyze?" + query)[0], 400)
            load.assert_not_called()

    def test_data_failure_is_explained_without_success_result(self):
        with patch("app.load_prices", side_effect=DataError("No local prices")):
            status, body, _ = self.request("/api/analyze?symbols=AAPL&benchmark=SPY&start=2025-01-01&end=2025-02-01")
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body), {"error": "No local prices"})


if __name__ == "__main__":
    unittest.main()
