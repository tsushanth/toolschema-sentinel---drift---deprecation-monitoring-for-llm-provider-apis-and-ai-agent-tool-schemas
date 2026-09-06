"""Model lifecycle diffing: deprecations, sunset-date changes, and removals."""

from lib.diff import Finding, BREAKING, WARNING, INFO


def diff_models(before_models, after_models):
    """Diff two provider model lists, matched by `id`."""
    before_by_id = {m["id"]: m for m in before_models}
    after_by_id = {m["id"]: m for m in after_models}
    findings = []

    for model_id in sorted(after_by_id.keys() - before_by_id.keys()):
        findings.append(Finding(
            kind="model_added",
            severity=INFO,
            provider="",
            model=model_id,
            detail=f"new model `{model_id}` available",
        ))

    for model_id in sorted(before_by_id.keys() - after_by_id.keys()):
        findings.append(Finding(
            kind="model_removed",
            severity=BREAKING,
            provider="",
            model=model_id,
            detail=f"model `{model_id}` was removed from the provider's model list",
        ))

    for model_id in sorted(before_by_id.keys() & after_by_id.keys()):
        before_model = before_by_id[model_id]
        after_model = after_by_id[model_id]
        before_deprecated = before_model.get("deprecated", False)
        after_deprecated = after_model.get("deprecated", False)
        before_sunset = before_model.get("sunset_date")
        after_sunset = after_model.get("sunset_date")

        if not before_deprecated and after_deprecated:
            detail = f"model `{model_id}` newly marked deprecated"
            if after_sunset:
                detail += f", sunset date `{after_sunset}`"
            findings.append(Finding(
                kind="model_deprecated",
                severity=WARNING,
                provider="",
                model=model_id,
                detail=detail,
                after=after_sunset,
            ))
        elif before_deprecated and after_deprecated and before_sunset != after_sunset:
            findings.append(Finding(
                kind="model_sunset_date_changed",
                severity=WARNING,
                provider="",
                model=model_id,
                detail=f"model `{model_id}` sunset date changed from `{before_sunset}` to `{after_sunset}`",
                before=before_sunset,
                after=after_sunset,
            ))

    return findings
