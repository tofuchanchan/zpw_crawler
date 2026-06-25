import unittest

from src.zpw_crawler.auth import hash_password, verify_password


class AuthTest(unittest.TestCase):
    def test_hash_and_verify_password(self):
        encoded = hash_password("correct-password")
        self.assertTrue(verify_password("correct-password", encoded))
        self.assertFalse(verify_password("wrong-password", encoded))

    def test_invalid_hash_returns_false(self):
        self.assertFalse(verify_password("password", "not-a-valid-hash"))


if __name__ == "__main__":
    unittest.main()
