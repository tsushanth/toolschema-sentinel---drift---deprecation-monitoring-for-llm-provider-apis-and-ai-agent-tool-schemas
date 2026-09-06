import unittest

from lib.diff import Finding, BREAKING, WARNING
from lib.impact import find_affected


REGISTRY = {
    "weather-agent": {"provider": "openai", "model": "gpt-4-turbo", "tools": ["get_weather"]},
    "legacy-support-bot": {"provider": "openai", "model": "gpt-3.5-turbo", "tools": ["create_ticket"]},
    "claude-writer": {"provider": "anthropic", "model": "claude-3-opus-20240229", "tools": ["draft_email"]},
}


class FindAffectedTests(unittest.TestCase):
    def test_tool_scoped_finding_flags_only_matching_tool(self):
        finding = Finding(
            kind="schema_required_added", severity=BREAKING, provider="openai", tool="get_weather", detail="..."
        )
        affected = find_affected([finding], REGISTRY)
        self.assertEqual({item["name"] for item in affected}, {"weather-agent"})

    def test_model_scoped_finding_flags_every_tool_on_that_model(self):
        finding = Finding(
            kind="model_deprecated", severity=WARNING, provider="openai", model="gpt-3.5-turbo", detail="..."
        )
        affected = find_affected([finding], REGISTRY)
        self.assertEqual({item["name"] for item in affected}, {"legacy-support-bot"})

    def test_unrelated_provider_not_flagged(self):
        finding = Finding(
            kind="model_removed", severity=BREAKING, provider="google", model="gemini-1.0-pro", detail="..."
        )
        self.assertEqual(find_affected([finding], REGISTRY), [])

    def test_unrelated_tool_on_same_provider_not_flagged(self):
        finding = Finding(kind="tool_removed", severity=BREAKING, provider="openai", tool="some_other_tool", detail="...")
        self.assertEqual(find_affected([finding], REGISTRY), [])

    def test_finding_with_no_model_or_tool_matches_provider_only(self):
        finding = Finding(kind="rate_limit_changed", severity=WARNING, provider="anthropic", detail="...")
        affected = find_affected([finding], REGISTRY)
        self.assertEqual({item["name"] for item in affected}, {"claude-writer"})


if __name__ == "__main__":
    unittest.main()
