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


import os
import tempfile


class FakeLatestClient:
    def get_tenant_operations(self, tid):
        return "<html>"

    def parse_operations(self, html, tid, name):
        return [
            {
                "tenant_id": tid, "tenant_name": name, "type": "FV",
                "date": date(2026, 1, 5), "income": 100.0, "expense": None,
                "balance": 100.0, "document": "INV1", "pdf_url": "/pdf/inv1",
                "status": "Paid", "description": "income",
            },
            {
                "tenant_id": tid, "tenant_name": name, "type": "WP",
                "date": date(2026, 1, 6), "income": 50.0, "expense": None,
                "balance": 150.0, "document": "PAY1", "pdf_url": "/pdf/pay1",
                "status": "Paid", "description": "payment",
            },
        ]

    def get_finances(self, page_size=100):
        return "<html>"

    def parse_finances(self, html):
        return [
            {
                "type": "FV", "date": date(2026, 1, 4), "payment": None,
                "charge": 200.0, "balance": None, "document": "COST1",
                "pdf_url": "/pdf/cost1", "status": "Paid", "description": "cost",
            },
        ]

    def get_estates(self):
        return [{"estate_id": 7}]

    def get_estate_cost_documents(self, eid):
        return "<html>"

    def parse_estate_cost_documents(self, html, owner_name=None):
        return [
            {
                "seller": "Owner Sp. z o.o.", "amount": 300.0,
                "date_added": date(2026, 1, 3), "sale_date": None,
                "number": "P1", "payment_deadline": None, "payment_date": None,
                "download_zip_url": None, "cost_document_id": 42,
            },
        ]

    def get_cost_document_download_url(self, cd_id):
        return "/pdf/payout"

    def download_file(self, url, dest):
        with open(dest, "wb") as f:
            f.write(b"%PDF")
        return True


RAW_TENANTS = [{"tenant_id": "1", "user_fullname": "Jan", "user_active": "1",
                "eah_owner_fullname": "Owner"}]


class TestLatestCompute(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.client = FakeLatestClient()

    def test_latest_invoices(self):
        with patch("lib.api_son.get_client", return_value=self.client), \
             patch("lib.api_son._get_raw_tenants", return_value=RAW_TENANTS), \
             patch("lib.api_son.out_dir", return_value=self.tmp):
            res = api_son.latest_invoices()
        self.assertIsNotNone(res.income_invoice)
        self.assertEqual(res.income_invoice.document, "INV1")
        self.assertIsNotNone(res.payment)
        self.assertEqual(res.payment.document, "PAY1")
        self.assertIsNotNone(res.cost_invoice)
        self.assertEqual(res.cost_invoice.document, "COST1")
        self.assertIsNotNone(res.payout)
        self.assertEqual(res.payout.cost_document_id, 42)
        self.assertEqual(res.last_document_date, "2026-01-06")
        self.assertEqual(res.warnings, [])

    def test_download_latest(self):
        with patch("lib.api_son.get_client", return_value=self.client), \
             patch("lib.api_son._get_raw_tenants", return_value=RAW_TENANTS), \
             patch("lib.api_son.out_dir", return_value=self.tmp):
            res = api_son.download_latest(force=True)
        self.assertTrue(res.state_updated)
        self.assertEqual(set(res.downloads.keys()), {"income_invoice", "cost_invoice", "payout", "payment"})
        for d in res.downloads.values():
            self.assertEqual(d.status, "saved")
            self.assertIsNotNone(d.path)
        # state file written
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "known_invoices.json")))

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            api_son.latest_invoices(types=["nope"])
        with self.assertRaises(ValueError):
            api_son.download_latest(types=["nope"])

    def test_skipped_types(self):
        with patch("lib.api_son.get_client", return_value=self.client), \
             patch("lib.api_son._get_raw_tenants", return_value=RAW_TENANTS), \
             patch("lib.api_son.out_dir", return_value=self.tmp):
            res = api_son.download_latest(types=["income_invoice"])
        self.assertEqual(res.downloads["cost_invoice"].status, "skipped")
        self.assertEqual(res.downloads["payout"].status, "skipped")
        self.assertEqual(res.downloads["payment"].status, "skipped")


if __name__ == "__main__":
    unittest.main()
