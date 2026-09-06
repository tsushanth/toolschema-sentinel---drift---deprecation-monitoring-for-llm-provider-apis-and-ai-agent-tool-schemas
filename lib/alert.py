"""Format diff+impact findings into a Slack Block Kit payload and optionally
POST it to a webhook.
"""

import json
import os
import urllib.request

from lib.diff import BREAKING, WARNING, INFO

_SEVERITY_EMOJI = {BREAKING: "\U0001F534", WARNING: "\U0001F7E1", INFO: "\U0001F535"}


def build_slack_payload(provider, findings, affected):
    breaking_count = sum(1 for f in findings if f.severity == BREAKING)
    warning_count = sum(1 for f in findings if f.severity == WARNING)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"ToolSchema Sentinel: {provider} drift detected"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{len(findings)}* change(s) found — "
                    f"*{breaking_count}* breaking, *{warning_count}* warning(s)."
                ),
            },
        },
    ]

    if findings:
        blocks.append({"type": "divider"})
        for finding in findings:
            emoji = _SEVERITY_EMOJI.get(finding.severity, "")
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{emoji} *{finding.severity}* — {finding.detail}"},
            })

    if affected:
        blocks.append({"type": "divider"})
        names = sorted({item["name"] for item in affected})
        lines = []
        for name in names:
            entry = next(item["entry"] for item in affected if item["name"] == name)
            lines.append(f"• `{name}` (uses {entry['provider']}/{entry['model']})")
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Affected registered tools/prompts:*\n" + "\n".join(lines)},
        })
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "No registered tools/prompts are affected."},
        })

    return {"blocks": blocks}


def send_webhook(payload, webhook_url=None):
    """POST the Slack payload to a webhook URL if one is configured.

    Returns True if a POST was attempted, False if no webhook was configured.
    """
    url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return False

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()
    return True
