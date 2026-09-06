import unittest

from lib.deprecations import diff_models
from lib.diff import BREAKING, WARNING


class DiffModelsTests(unittest.TestCase):
    def test_model_newly_deprecated(self):
        before = [{"id": "gpt-3.5-turbo", "deprecated": False, "sunset_date": None}]
        after = [{"id": "gpt-3.5-turbo", "deprecated": True, "sunset_date": "2026-12-01"}]
        findings = diff_models(before, after)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "model_deprecated")
        self.assertEqual(findings[0].severity, WARNING)
        self.assertEqual(findings[0].model, "gpt-3.5-turbo")

    def test_sunset_date_changed_on_already_deprecated_model(self):
        before = [{"id": "gpt-3.5-turbo", "deprecated": True, "sunset_date": "2026-12-01"}]
        after = [{"id": "gpt-3.5-turbo", "deprecated": True, "sunset_date": "2026-10-01"}]
        findings = diff_models(before, after)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "model_sunset_date_changed")

    def test_model_removed_is_breaking(self):
        before = [{"id": "gemini-1.0-pro", "deprecated": False, "sunset_date": None}]
        findings = diff_models(before, [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "model_removed")
        self.assertEqual(findings[0].severity, BREAKING)
        self.assertEqual(findings[0].model, "gemini-1.0-pro")

    def test_model_added_is_informational(self):
        after = [{"id": "gpt-5", "deprecated": False, "sunset_date": None}]
        findings = diff_models([], after)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "model_added")

    def test_unchanged_model_yields_no_findings(self):
        model = {"id": "gpt-4-turbo", "deprecated": False, "sunset_date": None}
        self.assertEqual(diff_models([model], [model]), [])


if __name__ == "__main__":
    unittest.main()
