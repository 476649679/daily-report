import unittest

from scripts.create_issue import issue_exists


class CreateIssueTests(unittest.TestCase):
    def test_issue_exists_matches_existing_title(self):
        issues = [
            {"title": "个人资讯简报 | 2026-04-20 早间"},
            {"title": "其他日报"},
        ]

        self.assertTrue(issue_exists(issues, "个人资讯简报 | 2026-04-20 早间"))
        self.assertFalse(issue_exists(issues, "个人资讯简报 | 2026-04-21 早间"))


if __name__ == "__main__":
    unittest.main()
