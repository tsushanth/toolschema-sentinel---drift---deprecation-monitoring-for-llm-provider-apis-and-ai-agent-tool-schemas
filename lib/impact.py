"""Cross-reference diff findings against the user's registered tools/prompts."""


def find_affected(findings, registry):
    """Return [{"name", "entry", "finding"}, ...] for registry entries impacted
    by a finding.

    Matching rules:
    - always requires matching `provider`
    - if the finding is model-scoped (e.g. a deprecation), it matches every
      registry entry pinned to that model, regardless of which tool they use
    - if the finding is tool-scoped (e.g. a schema change), it matches every
      registry entry that lists that tool, regardless of which model they use
    """
    affected = []
    for finding in findings:
        for name, entry in registry.items():
            if entry.get("provider") != finding.provider:
                continue
            if finding.model and entry.get("model") != finding.model:
                continue
            if finding.tool and finding.tool not in entry.get("tools", []):
                continue
            affected.append({"name": name, "entry": entry, "finding": finding})
    return affected
