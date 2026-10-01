"""Offline-Regressionen für den Issue-Lebenszyklus des Einzigartigkeits-Audits."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uniqueness_issue_sync as sync


class FakeIssuesApi:
    """Netzfreier Spy für den vollständigen Issue-Lebenszyklus."""

    open_issues = []
    instances = []

    def __init__(self, *args, **kwargs):
        self.created = []
        self.updated = []
        self.comments = []
        self.closed = []
        type(self).instances.append(self)

    def list_open(self):
        return list(type(self).open_issues)

    def create(self, body):
        self.created.append(body)
        return {"number": 777}

    def update(self, number, body):
        self.updated.append((number, body))

    def comment(self, number, body):
        self.comments.append((number, body))

    def close(self, number):
        self.closed.append(number)


class IssueSyncContractTests(unittest.TestCase):
    ENV = {
        "GITHUB_TOKEN": "test-token",
        "GITHUB_REPOSITORY": "frank-hartung/franksfinanzcheck-blog",
        "GITHUB_REF": "refs/heads/main",
        "UNIQUE_PRODUCTION_REF": "refs/heads/main",
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_RUN_ID": "123",
    }

    def setUp(self):
        FakeIssuesApi.open_issues = []
        FakeIssuesApi.instances = []

    def test_exact_title_ignores_pull_requests_and_other_issues(self):
        issues = [
            {"number": 490, "title": sync.ISSUE_TITLE},
            {"number": 491, "title": sync.ISSUE_TITLE, "pull_request": {"url": "x"}},
            {"number": 492, "title": "anderer Befund"},
        ]
        self.assertEqual([item["number"] for item in sync.matching_open_issues(issues)], [490])

    def test_only_expected_production_ref_can_mutate_issue_state(self):
        self.assertTrue(sync.is_production_ref("refs/heads/main", "refs/heads/main"))
        self.assertFalse(sync.is_production_ref("refs/heads/arena/audit", "refs/heads/main"))
        self.assertFalse(sync.is_production_ref("refs/heads/main", ""))

    def test_critical_body_is_readable_and_capped(self):
        body = sync.critical_body("Zeile\n" * (sync.REPORT_LIMIT + 1), "https://example.test/run/7")
        self.assertIn("Offener Bestandsbefund", body)
        self.assertIn("vollständiger Beleg im Workflow-Log", body)
        self.assertIn("https://example.test/run/7", body)
        # Body plus statischer Kontext bleibt deutlich unter dem GitHub-Limit.
        self.assertLess(len(body), 60_000)

    def test_resolution_comment_records_the_proof(self):
        comment = sync.resolution_comment("https://example.test/run/8")
        self.assertIn("Audit wieder grün", comment)
        self.assertIn("https://example.test/run/8", comment)

    def test_critical_run_updates_oldest_issue_and_closes_duplicates(self):
        FakeIssuesApi.open_issues = [
            {"number": 491, "title": sync.ISSUE_TITLE, "created_at": "2026-10-01T10:00:00Z"},
            {"number": 490, "title": sync.ISSUE_TITLE, "created_at": "2026-10-01T09:00:00Z"},
        ]
        with patch.object(sync, "GitHubIssuesApi", FakeIssuesApi):
            self.assertEqual(sync.sync("critical", "kritischer Beleg", self.ENV), 0)
        api = FakeIssuesApi.instances[0]
        self.assertEqual([number for number, _ in api.updated], [490])
        self.assertIn("kritischer Beleg", api.updated[0][1])
        self.assertEqual(api.closed, [491])
        self.assertIn("#490", api.comments[0][1])

    def test_clean_run_comments_and_closes_every_stale_matching_issue(self):
        FakeIssuesApi.open_issues = [
            {"number": 490, "title": sync.ISSUE_TITLE},
            {"number": 491, "title": sync.ISSUE_TITLE},
            {"number": 900, "title": "anderer Befund"},
        ]
        with patch.object(sync, "GitHubIssuesApi", FakeIssuesApi):
            self.assertEqual(sync.sync("clean", "", self.ENV), 0)
        api = FakeIssuesApi.instances[0]
        self.assertEqual(api.closed, [490, 491])
        self.assertEqual([number for number, _ in api.comments], [490, 491])
        self.assertTrue(all("Audit wieder grün" in body for _, body in api.comments))

    def test_non_production_branch_may_not_touch_the_issue_api(self):
        env = {**self.ENV, "GITHUB_REF": "refs/heads/arena/audit"}
        with patch.object(sync, "GitHubIssuesApi", FakeIssuesApi):
            self.assertEqual(sync.sync("clean", "", env), 0)
        self.assertEqual(FakeIssuesApi.instances, [])

    def test_embedded_selftest_is_green(self):
        self.assertEqual(sync.selftest(), [])


if __name__ == "__main__":
    unittest.main()
