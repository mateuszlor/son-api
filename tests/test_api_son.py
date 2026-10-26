import unittest
from unittest.mock import patch, MagicMock
from datetime import date

from lib import api_son
from lib.api_models import TenantOut, OperationOut


class FakeClient:
    def get_tenants(self):
        return [
            {"tenant_id": "1", "user_fullname": "Jan", "user_active": "1",
             "user_balance": "10,5", "estate_id": "5"},
        ]

    def get_tenant_operations(self, tid):
        return "<html></html>"

    def parse_operations(self, html, tid, name):
        return [{
            "tenant_id": 1, "tenant_name": name, "type": "FV",
            "date": date(2026, 1, 2), "date_raw": "02/01/2026",
            "income": 10.5, "expense": None, "balance": 10.5,
            "document": "doc1", "pdf_url": "/x", "status": "Opłacona",
            "description": "desc",
        }]


class TestApiSon(unittest.TestCase):
    def test_list_tenants_conversion(self):
        with patch("lib.api_son.get_client", return_value=FakeClient()):
            # reset tenant name cache
            api_son._tenants_raw_cache = None
            api_son._tenants_raw_cache_time = 0.0
            res = api_son.list_tenants()
        self.assertEqual(len(res), 1)
        self.assertIsInstance(res[0], TenantOut)
        self.assertEqual(res[0].tenant_id, 1)
        self.assertTrue(res[0].user_active)
        self.assertEqual(res[0].user_balance, 10.5)
        self.assertEqual(res[0].estate_id, 5)

    def test_tenant_operations_conversion(self):
        with patch("lib.api_son.get_client", return_value=FakeClient()):
            pass
            res = api_son.tenant_operations("1")
        self.assertEqual(len(res), 1)
        self.assertIsInstance(res[0], OperationOut)
        self.assertEqual(res[0].date, "2026-01-02")
        self.assertEqual(res[0].income, 10.5)


if __name__ == "__main__":
    unittest.main()
