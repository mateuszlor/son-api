import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api_server import app


class TestApiSmoke(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        with patch("lib.api_son.get_client", side_effect=RuntimeError("no panel")):
            r = self.client.get("/health")
        self.assertEqual(r.status_code, 503)

    def test_health_live(self):
        r = self.client.get("/health/live")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_health_ready(self):
        with patch("lib.api_son.panel_ping", side_effect=RuntimeError("no panel")):
            r = self.client.get("/health/ready")
        self.assertEqual(r.status_code, 503)

    def test_docs(self):
        r = self.client.get("/docs")
        self.assertEqual(r.status_code, 200)

    def test_openapi(self):
        r = self.client.get("/openapi.json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("paths", r.json())

    def test_artifact_missing(self):
        r = self.client.get("/v1/artifacts/does-not-exist.txt")
        self.assertEqual(r.status_code, 404)

    def test_artifact_traversal(self):
        from lib.path_safety import safe_resolve
        import tempfile, os
        base = tempfile.mkdtemp()
        self.assertIsNone(safe_resolve(base, "../README.md"))


if __name__ == "__main__":
    unittest.main()
