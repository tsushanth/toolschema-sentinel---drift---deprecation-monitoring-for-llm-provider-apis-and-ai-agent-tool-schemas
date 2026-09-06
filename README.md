# ToolSchema Sentinel — Local MVP

Drift and deprecation monitoring for LLM provider APIs and AI-agent tool
schemas. This is a local proof-of-value scaffold, not a hosted service: it
proves that diffing two snapshots of a provider's models / function-calling
schemas / rate limits, then cross-referencing the delta against your own
registered tools, produces a precise, actionable alert — before an agent
starts emitting malformed tool calls or a model gets sunset under you.

## What it does

Given a `before` and `after` JSON snapshot of an LLM provider (what a real
ingestion job would have pulled from OpenAI/Anthropic/Google docs or API
responses) and a `registry.json` describing which of your tools/prompts
depend on which provider/model/tool, `sentinel.py` will:

1. Diff the two snapshots for:
   - **Schema changes** — a function-calling parameter added, removed,
     retyped, or moved between optional and required.
   - **Model lifecycle changes** — a model newly marked deprecated, its
     sunset date changing, or a model disappearing from the list entirely.
   - **Rate-limit changes** — a per-model `rpm`/`tpm` field changing (tightened
     limits are flagged as warnings).
2. Cross-reference every change against `registry.json` to name exactly
   which of *your* tools/prompts are affected, and why.
3. Print a human-readable report, then a Slack Block Kit JSON payload
   representing the alert — and actually POST it if `SLACK_WEBHOOK_URL` is
   set (or `--webhook` is passed).

No live API polling, no database, no UI, no accounts — just a CLI over flat
JSON files, using only the Python standard library.

## Requirements

Python 3.10+. No dependencies, no install step.

## Run the demo

```bash
python3 sentinel.py diff \
  --provider openai \
  --before snapshots/openai/before.json \
  --after snapshots/openai/after.json \
  --registry registry.json
```

This reports (among other things):

- `gpt-3.5-turbo` newly marked deprecated → flags `legacy-support-bot`
- `gpt-4-turbo`'s `rpm` rate limit tightened → flags `weather-agent`
- `create_ticket`'s parameters gained a new required field `customer_id` →
  flags `legacy-support-bot`
- `get_weather`'s `units` parameter became required → flags `weather-agent`

...then prints the Slack Block Kit payload that would be sent.

Try the other two bundled providers the same way:

```bash
python3 sentinel.py diff --provider anthropic \
  --before snapshots/anthropic/before.json --after snapshots/anthropic/after.json
python3 sentinel.py diff --provider google \
  --before snapshots/google/before.json --after snapshots/google/after.json
```

**Prove there are no false positives** by diffing a snapshot against itself:

```bash
python3 sentinel.py diff --provider openai \
  --before snapshots/openai/before.json --after snapshots/openai/before.json
```

This should report "No changes detected" and an empty Slack alert.

### Sending a real Slack alert

Slack incoming webhooks need no OAuth — export the URL and the CLI will POST
the payload automatically:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
python3 sentinel.py diff --provider openai --before ... --after ...
```

To inspect the request locally instead of hitting real Slack, point
`--webhook` at `python3 -m http.server` or a throwaway request-bin URL.

### CI-style gating

`check` runs the same diff but exits non-zero if any **breaking** change is
found — useful as a build step to catch drift before it reaches production:

```bash
python3 sentinel.py check --provider openai \
  --before snapshots/openai/before.json --after snapshots/openai/after.json
```

## Data model

- **Snapshot** (`snapshots/<provider>/{before,after}.json`) — a normalized
  representation of what an ingestion job would pull from a provider:
  `models` (id, deprecated flag, sunset date), `rate_limits` (per-model rpm/
  tpm), and `tools` (function-calling name + JSON Schema `parameters`). The
  same shape is used for OpenAI, Anthropic, and Google fixtures to prove the
  diff/impact logic is provider-agnostic.
- **Registry** (`registry.json`) — maps each of your tools/prompts to the
  `provider`, `model`, and list of `tools` (function names) it depends on.

## Layout

```
sentinel.py              CLI entrypoint (`diff` and `check` subcommands)
registry.json             sample registry of tools/prompts and what they depend on
snapshots/<provider>/     sample before/after snapshot pairs (openai, anthropic, google)
lib/diff.py               recursive JSON-Schema diff: fields, types, required-list
lib/deprecations.py       model lifecycle diff: deprecated/sunset/removed
lib/impact.py             cross-references diff findings against registry.json
lib/alert.py              builds the Slack Block Kit payload, optional webhook POST
tests/                    unit tests for diff, deprecations, and impact logic
```

## Tests

```bash
python3 -m unittest discover tests
```

Covers: a required parameter added to a schema, a parameter type change, a
field added/removed, a model marked deprecated, a model removed entirely, a
rate-limit change, and that impact-mapping flags exactly the registered
tools that reference the affected model/tool — no more, no less.

## What's intentionally out of scope

Auth/accounts, billing, hosting, live polling of real provider APIs, a real
Slack app install, and scheduling/continuous background monitoring are all
out of scope for this local proof of value. See `plan.md` for the full
rationale.
