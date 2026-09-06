# ToolSchema Sentinel — Local MVP Scaffold Plan

## Goal

Prove the core value locally: given a "before" and "after" snapshot of an LLM
provider's models/tool-schemas/rate-limits, detect the exact delta (schema
change, deprecation, rate-limit change), cross-reference it against a
user-registered list of tools/prompts, and emit an alert (Slack-formatted
message block, printed to console and optionally POSTed to a webhook) that
says precisely which of the user's tools are affected and why.

No live API polling, no persistence service, no UI — just a CLI that takes
two JSON snapshots and a registry file, and produces a diff + impact + alert.

## 1. Stack

**Plain Python 3, standard library only.**

- No build step, no package.json/venv ceremony required to run the demo —
  `python3 sentinel.py ...` just works on any machine with Python 3.10+.
- `json`, `argparse`, `dataclasses`, `urllib.request`, `unittest` from stdlib
  cover everything needed: loading snapshots, diffing nested JSON Schema
  objects, and optionally POSTing a webhook.
- No external dependencies (no `requests`, no `deepdiff`) — a recursive
  JSON-schema diff is ~50 lines of plain code and avoids adding install
  friction to a scaffold whose only job is to demonstrate the idea.
- Rejected alternatives: Node/TS (adds tsconfig/build/npm-install overhead
  for no real benefit — JSON diffing is not TS's strong suit here); Go
  single-binary (nice for later packaging, but compilation is unnecessary
  ceremony for a first local proof of value).

## 2. Explicitly out of scope for this MVP

- **Auth / accounts** — single local user, no login, no multi-tenant registry.
- **Billing** — not applicable to a local proof of value.
- **Hosting / deployment** — runs on a laptop via CLI only, nothing is served.
- **Live polling of real provider APIs/docs** — instead, the demo ships
  canned "before" and "after" JSON snapshot fixtures that represent what a
  real ingestion job would have pulled from OpenAI/Anthropic/Google docs or
  API responses. (Building a real scraper/poller per provider is a
  separate, later concern — the thing to prove first is that the diff +
  impact-mapping logic is valuable, not the ingestion pipeline.)
- **Real Slack app / OAuth integration** — the alert step only builds a
  Slack Block Kit–shaped JSON payload and prints it; it will POST to a
  webhook URL only if one is supplied via an env var (Slack incoming
  webhooks need no OAuth/app install, so this stays a one-line `urllib`
  call, not a scoped-out dependency).
- **Scheduling / continuous background monitoring** — the CLI runs once per
  invocation on two given snapshots; a `--watch` loop or cron wrapper is a
  future concern, not needed to demonstrate the core diff+alert value.
- **Database** — snapshots and the tool registry are flat JSON files on disk.
- **Every provider** — fixtures cover OpenAI, Anthropic, and Google shapes
  (function-calling schema + model-list-with-deprecation fields) since that's
  enough to prove the provider-agnostic diff/impact logic generalizes.

## 3. File / directory layout

```
toolschema-sentinel/
├── sentinel.py              # CLI entrypoint (argparse): `diff` and `check` subcommands
├── registry.json            # sample user registry: tool/prompt name -> {provider, model, schema path/ref it depends on}
├── snapshots/
│   ├── openai/
│   │   ├── before.json      # sample prior snapshot: models list + function-calling tool schemas
│   │   └── after.json       # sample new snapshot with an introduced breaking change
│   ├── anthropic/
│   │   ├── before.json
│   │   └── after.json
│   └── google/
│       ├── before.json
│       └── after.json
├── lib/
│   ├── diff.py               # recursive JSON/JSON-Schema diff: added/removed fields, type changes, required-list changes
│   ├── deprecations.py       # detects model entries newly marked deprecated/sunset, or removed outright
│   ├── impact.py             # cross-references a diff's changed paths/models against registry.json
│   └── alert.py              # formats findings into a Slack Block Kit payload; optional urllib POST if SLACK_WEBHOOK_URL is set
├── tests/
│   ├── test_diff.py          # unit tests: schema field added/removed/retyped, required-list changed
│   ├── test_deprecations.py  # unit tests: model deprecated/sunset/removed detection
│   └── test_impact.py        # unit tests: correct registered tools are flagged, unrelated tools are not
└── README.md                 # one-page: what this proves, how to run it
```

## 4. Verification

**Automated:**
- `python3 -m unittest discover tests` — unit tests on hand-crafted
  before/after fixture pairs covering: a required parameter added to a
  function-calling schema, a parameter type changed, a model flagged
  deprecated, a model removed entirely, and a rate-limit field changed.
  Each test asserts the diff engine reports the exact delta and
  `impact.py` correctly maps it to the registered tool(s) that reference
  that model/schema (and does *not* flag unrelated registered tools).

**Manual run-through (the actual demo):**
```
python3 sentinel.py diff \
  --provider openai \
  --before snapshots/openai/before.json \
  --after snapshots/openai/after.json \
  --registry registry.json
```
Expected observable output:
1. A human-readable delta report (e.g. "function `get_weather`: parameter
   `units` changed from optional to required").
2. A list of affected registered tools/prompts pulled from `registry.json`
   (e.g. "affected: `weather-agent` (uses openai/gpt-x, tool `get_weather`)").
3. A printed Slack Block Kit JSON payload representing the alert that would
   be sent (and, if `SLACK_WEBHOOK_URL` is exported, an actual POST to that
   URL — testable locally with a throwaway webhook or a tool like
   `nc -l`/`python3 -m http.server` to inspect the request).

Repeating the same run against a before/after pair with no meaningful
changes should confirm the tool emits no false-positive alert — that's the
other half of proving the diff logic is trustworthy.
