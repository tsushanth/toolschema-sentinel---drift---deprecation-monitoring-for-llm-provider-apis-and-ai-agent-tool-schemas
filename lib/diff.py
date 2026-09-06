"""Recursive JSON / JSON-Schema diff for function-calling tool schemas.

This module is provider-agnostic: it operates on the normalized internal
snapshot shape (see README.md), not on any single vendor's raw API response.
"""

from dataclasses import dataclass
from typing import Any, Optional

BREAKING = "BREAKING"
WARNING = "WARNING"
INFO = "INFO"


@dataclass
class Finding:
    kind: str
    severity: str
    provider: str
    detail: str
    model: Optional[str] = None
    tool: Optional[str] = None
    path: Optional[str] = None
    before: Any = None
    after: Any = None


def _join(path, key):
    return f"{path}.{key}" if path else key


def diff_json_schema(before, after, path="parameters"):
    """Diff two JSON Schema objects (as used in a function-calling `parameters` block).

    Detects type changes, added/removed properties (recursing into nested
    objects), and required-list changes. Returns a list of Finding objects;
    provider/tool are left blank for the caller to fill in.
    """
    findings = []

    before_type = before.get("type") if isinstance(before, dict) else None
    after_type = after.get("type") if isinstance(after, dict) else None
    if before_type != after_type:
        findings.append(Finding(
            kind="schema_type_changed",
            severity=BREAKING,
            provider="",
            detail=f"`{path}` type changed from `{before_type}` to `{after_type}`",
            path=path,
            before=before_type,
            after=after_type,
        ))

    before_props = before.get("properties", {}) if isinstance(before, dict) else {}
    after_props = after.get("properties", {}) if isinstance(after, dict) else {}
    before_required = set(before.get("required", []) if isinstance(before, dict) else [])
    after_required = set(after.get("required", []) if isinstance(after, dict) else [])

    for name in sorted(after_props.keys() - before_props.keys()):
        now_required = name in after_required
        findings.append(Finding(
            kind="schema_field_added",
            severity=BREAKING if now_required else INFO,
            provider="",
            detail=(
                f"`{path}` gained {'required' if now_required else 'optional'} "
                f"field `{name}`"
            ),
            path=_join(path, name),
            after=after_props[name],
        ))

    for name in sorted(before_props.keys() - after_props.keys()):
        findings.append(Finding(
            kind="schema_field_removed",
            severity=BREAKING,
            provider="",
            detail=f"`{path}` lost field `{name}`",
            path=_join(path, name),
            before=before_props[name],
        ))

    for name in sorted(before_props.keys() & after_props.keys()):
        findings.extend(diff_json_schema(before_props[name], after_props[name], path=_join(path, name)))

    for name in sorted(after_required - before_required):
        if name in before_props:  # newly-added fields are already reported above
            findings.append(Finding(
                kind="schema_required_added",
                severity=BREAKING,
                provider="",
                detail=f"`{path}` field `{name}` changed from optional to required",
                path=_join(path, name),
            ))

    for name in sorted(before_required - after_required):
        if name in after_props:
            findings.append(Finding(
                kind="schema_required_removed",
                severity=INFO,
                provider="",
                detail=f"`{path}` field `{name}` changed from required to optional",
                path=_join(path, name),
            ))

    return findings


def diff_tools(before_tools, after_tools):
    """Diff two lists of function-calling tool definitions, matched by name."""
    before_by_name = {t["name"]: t for t in before_tools}
    after_by_name = {t["name"]: t for t in after_tools}
    findings = []

    for name in sorted(after_by_name.keys() - before_by_name.keys()):
        findings.append(Finding(
            kind="tool_added",
            severity=INFO,
            provider="",
            tool=name,
            detail=f"new tool `{name}` introduced",
        ))

    for name in sorted(before_by_name.keys() - after_by_name.keys()):
        findings.append(Finding(
            kind="tool_removed",
            severity=BREAKING,
            provider="",
            tool=name,
            detail=f"tool `{name}` was removed",
        ))

    for name in sorted(before_by_name.keys() & after_by_name.keys()):
        before_params = before_by_name[name].get("parameters", {})
        after_params = after_by_name[name].get("parameters", {})
        for finding in diff_json_schema(before_params, after_params, path="parameters"):
            finding.tool = name
            finding.detail = f"tool `{name}`: {finding.detail}"
            findings.append(finding)

    return findings


def diff_rate_limits(before_limits, after_limits):
    """Diff per-model rate-limit dicts, e.g. {"gpt-4-turbo": {"rpm": 500, "tpm": 300000}}."""
    findings = []
    for model in sorted(before_limits.keys() & after_limits.keys()):
        before_fields = before_limits[model]
        after_fields = after_limits[model]
        for field_name in sorted(before_fields.keys() | after_fields.keys()):
            before_val = before_fields.get(field_name)
            after_val = after_fields.get(field_name)
            if before_val == after_val:
                continue
            tightened = (
                isinstance(before_val, (int, float))
                and isinstance(after_val, (int, float))
                and after_val < before_val
            )
            findings.append(Finding(
                kind="rate_limit_changed",
                severity=WARNING if tightened else INFO,
                provider="",
                model=model,
                detail=f"model `{model}` rate limit `{field_name}` changed from `{before_val}` to `{after_val}`",
                path=f"rate_limits.{model}.{field_name}",
                before=before_val,
                after=after_val,
            ))
    return findings
