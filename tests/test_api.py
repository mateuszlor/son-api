import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api_server import app
from lib.api_models import LatestOut, LatestDownloadOut, LatestDownloadResult, ArtifactLink


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
        r = self.client.get("/v1/artifacts/%2e%2e%2fREADME.md")
        self.assertEqual(r.status_code, 404)


class TestLatestEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_latest_get(self):
        with patch("api_server.latest_invoices", return_value=LatestOut(warnings=["w"])):
            r = self.client.get("/v1/latest")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["warnings"], ["w"])

    def test_latest_download(self):
        dd = LatestDownloadOut(downloads={
            "income_invoice": LatestDownloadResult(
                kind="income_invoice", status="saved", path="x.pdf",
                url=ArtifactLink(relative="/v1/artifacts/x.pdf", absolute="/v1/artifacts/x.pdf"),
            )
        })
        with patch("api_server.download_latest", return_value=dd):
            r = self.client.post("/v1/latest/download", json={})
        self.assertEqual(r.status_code, 200)
        url = r.json()["downloads"]["income_invoice"]["url"]["absolute"]
        self.assertTrue(url.startswith("http://testserver/"))

    def test_latest_download_invalid_type(self):
        r = self.client.post("/v1/latest/download", json={"types": ["nope"]})
        self.assertEqual(r.status_code, 400)

    def test_latest_download_value_error(self):
        with patch("api_server.download_latest", side_effect=ValueError("bad")):
            r = self.client.post("/v1/latest/download", json={})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
