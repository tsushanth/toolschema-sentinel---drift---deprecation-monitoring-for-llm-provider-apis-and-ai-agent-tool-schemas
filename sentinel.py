#!/usr/bin/env python3
"""ToolSchema Sentinel CLI.

Diffs a "before" and "after" snapshot of an LLM provider's models, tool
(function-calling) schemas, and rate limits, cross-references the delta
against a registry of your own tools/prompts, and prints the affected ones
plus a Slack-formatted alert.
"""

import argparse
import json
import sys

from lib.diff import diff_tools, diff_rate_limits, BREAKING
from lib.deprecations import diff_models
from lib.impact import find_affected
from lib.alert import build_slack_payload, send_webhook


def load_json(path):
    with open(path) as f:
        return json.load(f)


def compute_findings(provider, before, after):
    findings = []
    findings.extend(diff_models(before.get("models", []), after.get("models", [])))
    findings.extend(diff_rate_limits(before.get("rate_limits", {}), after.get("rate_limits", {})))
    findings.extend(diff_tools(before.get("tools", []), after.get("tools", [])))
    for finding in findings:
        finding.provider = provider
    return findings


def print_report(provider, findings, affected):
    print(f"\n=== ToolSchema Sentinel: {provider} drift report ===\n")
    if not findings:
        print("No changes detected between snapshots.\n")
        return

    for finding in findings:
        print(f"[{finding.severity}] {finding.detail}")

    print()
    if affected:
        print("Affected registered tools/prompts:")
        seen = set()
        for item in affected:
            key = (item["name"], item["finding"].detail)
            if key in seen:
                continue
            seen.add(key)
            entry = item["entry"]
            print(
                f"  - {item['name']} (uses {entry['provider']}/{entry['model']}, "
                f"tools={entry.get('tools', [])}) — {item['finding'].detail}"
            )
    else:
        print("No registered tools/prompts are affected.")
    print()


def cmd_diff(args):
    before = load_json(args.before)
    after = load_json(args.after)
    registry = load_json(args.registry)

    findings = compute_findings(args.provider, before, after)
    affected = find_affected(findings, registry)

    print_report(args.provider, findings, affected)

    payload = build_slack_payload(args.provider, findings, affected)
    print("=== Slack Block Kit payload ===\n")
    print(json.dumps(payload, indent=2))

    sent = send_webhook(payload, webhook_url=args.webhook)
    if sent:
        print("\nPosted alert to the configured Slack webhook.")
    elif findings:
        print("\n(no SLACK_WEBHOOK_URL set — alert printed above only)")

    return 0


def cmd_check(args):
    before = load_json(args.before)
    after = load_json(args.after)
    registry = load_json(args.registry)

    findings = compute_findings(args.provider, before, after)
    affected = find_affected(findings, registry)
    breaking = [f for f in findings if f.severity == BREAKING]

    print(
        f"{args.provider}: {len(findings)} change(s), {len(breaking)} breaking, "
        f"{len({a['name'] for a in affected})} tool(s)/prompt(s) affected"
    )
    for finding in breaking:
        print(f"  [BREAKING] {finding.detail}")

    return 1 if breaking else 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="sentinel.py",
        description="Diff LLM provider snapshots and alert on drift affecting your tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_args(subparser):
        subparser.add_argument("--provider", required=True, help="Provider name, e.g. openai, anthropic, google")
        subparser.add_argument("--before", required=True, help="Path to the 'before' snapshot JSON")
        subparser.add_argument("--after", required=True, help="Path to the 'after' snapshot JSON")
        subparser.add_argument("--registry", default="registry.json", help="Path to the tool/prompt registry JSON")

    diff_parser = subparsers.add_parser("diff", help="Report the full delta, impact, and Slack alert payload")
    add_common_args(diff_parser)
    diff_parser.add_argument("--webhook", default=None, help="Slack webhook URL (overrides SLACK_WEBHOOK_URL env var)")
    diff_parser.set_defaults(func=cmd_diff)

    check_parser = subparsers.add_parser("check", help="Exit non-zero if any breaking change is found (for CI)")
    add_common_args(check_parser)
    check_parser.set_defaults(func=cmd_check)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
