import unittest

from lib.diff import diff_json_schema, diff_tools, diff_rate_limits, BREAKING, INFO


class DiffJsonSchemaTests(unittest.TestCase):
    def test_field_added_and_required_is_breaking(self):
        before = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
        after = {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
            "required": ["a", "b"],
        }
        findings = diff_json_schema(before, after)
        added = next(f for f in findings if f.kind == "schema_field_added")
        self.assertEqual(added.severity, BREAKING)

    def test_field_added_optional_is_info(self):
        before = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
        after = {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
            "required": ["a"],
        }
        findings = diff_json_schema(before, after)
        added = next(f for f in findings if f.kind == "schema_field_added")
        self.assertEqual(added.severity, INFO)

    def test_field_removed_is_breaking(self):
        before = {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
            "required": ["a"],
        }
        after = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
        findings = diff_json_schema(before, after)
        self.assertTrue(any(f.kind == "schema_field_removed" and f.severity == BREAKING for f in findings))

    def test_type_changed_is_breaking(self):
        before = {"type": "object", "properties": {"units": {"type": "string"}}, "required": []}
        after = {"type": "object", "properties": {"units": {"type": "array"}}, "required": []}
        findings = diff_json_schema(before, after)
        changed = next(f for f in findings if f.kind == "schema_type_changed")
        self.assertEqual(changed.severity, BREAKING)
        self.assertEqual(changed.before, "string")
        self.assertEqual(changed.after, "array")

    def test_required_list_added_is_breaking(self):
        before = {"type": "object", "properties": {"units": {"type": "string"}}, "required": []}
        after = {"type": "object", "properties": {"units": {"type": "string"}}, "required": ["units"]}
        findings = diff_json_schema(before, after)
        self.assertTrue(
            any(f.kind == "schema_required_added" and f.severity == BREAKING for f in findings)
        )

    def test_required_list_removed_is_info(self):
        before = {"type": "object", "properties": {"units": {"type": "string"}}, "required": ["units"]}
        after = {"type": "object", "properties": {"units": {"type": "string"}}, "required": []}
        findings = diff_json_schema(before, after)
        self.assertTrue(
            any(f.kind == "schema_required_removed" and f.severity == INFO for f in findings)
        )

    def test_no_changes_yields_no_findings(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
        self.assertEqual(diff_json_schema(schema, schema), [])


class DiffToolsTests(unittest.TestCase):
    def test_tool_removed_is_breaking(self):
        before = [{"name": "get_weather", "parameters": {"type": "object", "properties": {}, "required": []}}]
        findings = diff_tools(before, [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "tool_removed")
        self.assertEqual(findings[0].severity, BREAKING)

    def test_tool_added_is_info(self):
        after = [{"name": "get_weather", "parameters": {"type": "object", "properties": {}, "required": []}}]
        findings = diff_tools([], after)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "tool_added")
        self.assertEqual(findings[0].severity, INFO)

    def test_unchanged_tools_yield_no_findings(self):
        tool = {
            "name": "get_weather",
            "parameters": {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]},
        }
        self.assertEqual(diff_tools([tool], [tool]), [])

    def test_schema_findings_are_tagged_with_tool_name(self):
        before = [
            {
                "name": "get_weather",
                "parameters": {"type": "object", "properties": {"units": {"type": "string"}}, "required": []},
            }
        ]
        after = [
            {
                "name": "get_weather",
                "parameters": {"type": "object", "properties": {"units": {"type": "string"}}, "required": ["units"]},
            }
        ]
        findings = diff_tools(before, after)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].tool, "get_weather")


class DiffRateLimitsTests(unittest.TestCase):
    def test_rate_limit_tightened_is_warning(self):
        before = {"gpt-4-turbo": {"rpm": 500, "tpm": 300000}}
        after = {"gpt-4-turbo": {"rpm": 300, "tpm": 300000}}
        findings = diff_rate_limits(before, after)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "rate_limit_changed")
        self.assertEqual(findings[0].severity, "WARNING")
        self.assertEqual(findings[0].model, "gpt-4-turbo")

    def test_rate_limit_loosened_is_info(self):
        before = {"gpt-4-turbo": {"rpm": 500, "tpm": 300000}}
        after = {"gpt-4-turbo": {"rpm": 800, "tpm": 300000}}
        findings = diff_rate_limits(before, after)
        self.assertEqual(findings[0].severity, INFO)

    def test_unchanged_rate_limits_yield_no_findings(self):
        limits = {"gpt-4-turbo": {"rpm": 500, "tpm": 300000}}
        self.assertEqual(diff_rate_limits(limits, limits), [])


if __name__ == "__main__":
    unittest.main()
