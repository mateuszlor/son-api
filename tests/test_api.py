import unittest

from fastapi.testclient import TestClient

from api_server import app


class TestApiSmoke(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        r = self.client.get("/health")
        self.assertIn(r.status_code, (200, 503))
        if r.status_code == 200:
            data = r.json()
            self.assertEqual(data["status"], "ok")
            self.assertIn("son_connected", data)

    def test_health_live(self):
        r = self.client.get("/health/live")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_health_ready(self):
        r = self.client.get("/health/ready")
        self.assertIn(r.status_code, (200, 503))

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
        r = self.client.get("/v1/artifacts/../README.md")
        self.assertIn(r.status_code, (400, 404, 422))


if __name__ == "__main__":
    unittest.main()
