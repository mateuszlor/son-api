import os
import tempfile
import unittest

from lib.path_safety import safe_resolve


class TestPathSafety(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()

    def test_allows_file_under_base(self):
        path = os.path.join(self.base, "a.txt")
        with open(path, "w") as f:
            f.write("x")
        res = safe_resolve(self.base, "a.txt")
        self.assertEqual(res, os.path.realpath(path))

    def test_rejects_traversal(self):
        self.assertIsNone(safe_resolve(self.base, "../secret.txt"))
        self.assertIsNone(safe_resolve(self.base, "sub/../../secret.txt"))

    def test_rejects_absolute_escape(self):
        self.assertIsNone(safe_resolve(self.base, "/etc/passwd"))

    def test_rejects_empty(self):
        self.assertIsNone(safe_resolve(self.base, ""))
        self.assertIsNone(safe_resolve(self.base, None))


if __name__ == "__main__":
    unittest.main()
