# `flows.json` v1 — schema reference

This is the human-readable reference for the `flows.json` v1 data format. The skill emits it, the renderer reads it, and CI validates against it on every PR.

For the runtime declaration the skill consults, see [`skills/codestory/references/schema.md`](../skills/codestory/references/schema.md). This document mirrors that file's rules but reads top-to-bottom for someone editing a `flows.json` by hand.

Related:

- [`docs/DISCOVERY.md`](./DISCOVERY.md) — how the skill arrives at a `flows.json` from a real codebase.
- [`docs/THEMES.md`](./THEMES.md) — what the renderer does with the JSON once it has one.

---

## Top-level shape

The file is a JSON object with three required keys:

```json
{
  "units":    [ Unit,  ... ],
  "flows":    [ Flow,  ... ],
  "glossary": { "term": "definition", ... }
}
```

- `units` — every service, package, app, or module a step references. Every `from` and `to` in every step must resolve to a unit id declared here.
- `flows` — the stories. Each flow is one runtime path through the system, ordered by execution.
- `glossary` — term to one-sentence definition mapping. The renderer alphabetises and shows them in a side panel.

No other top-level keys are required. Fixtures may carry extra keys (`project_name`, `actors`, `categories`) for the legacy renderer; the v1 schema declares the three above as canonical.

---

## `Unit`

```json
{
  "id":    "app",
  "kind":  "service",
  "label": "FastAPI app",
  "role":  "The application process; routes, dependencies, and the BackgroundTasks queue."
}
```

| Field   | Type   | Notes |
|---------|--------|-------|
| `id`    | string | kebab-case, unique across the file. The stable key. |
| `kind`  | string | one of `service`, `package`, `app`, `module`. Drives the chip style. |
| `label` | string | Title Case display name. |
| `role`  | string | One sentence on what the unit exists to do. |

---

## `Flow`

```json
{
  "id":        "create-order",
  "category":  "user",
  "title":     "Customer creates an order",
  "narration": "An external client POSTs an order to the FastAPI app, which inserts a row into Postgres and queues a background task before returning 201.",
  "steps":     [ Step, ... ]
}
```

| Field       | Type   | Notes |
|-------------|--------|-------|
| `id`        | string | kebab-case, unique across `flows[]`. The merge key for hand-edit preservation. |
| `category`  | string | one of the four chapters below. |
| `title`     | string | chapter-title-style story name shown at the top of the scene panel. |
| `narration` | string | One to three sentences naming trigger and outcome. Per-step prose lives on the steps. |
| `steps`     | array  | `Step` objects in execution order. |

### The four chapters

`category` is one of exactly these, no more, no less:

- `user` — the trigger is a human action against a UI or public API. Sign-up, post a message, click a button.
- `internal` — the trigger is one service calling another. Service-to-service RPC, queue producer to consumer.
- `background` — the trigger is a scheduler. Cron, Celery beat, Kubernetes CronJob, GitHub Actions schedule.
- `build` — the trigger is a developer action against the build / deploy surface. CI run, docker image build, database migration.

A flow lives in exactly one chapter, picked by the primary trigger. The CI `validate-examples` job rejects any other value.

---

## `Step`

```json
{
  "from":      "app",
  "to":        "db",
  "transport": "SQL",
  "payload":   "INSERT INTO orders (id, customer_id, amount_cents, currency, status, created_at) VALUES (...)",
  "note":      "src=app/routes/orders.py:48",
  "unknown":   false
}
```

| Field       | Type   | Notes |
|-------------|--------|-------|
| `from`      | string | references a `Unit.id`. The step's source. |
| `to`        | string | references a `Unit.id`. The step's destination. |
| `transport` | string | the wire shape: `HTTP POST`, `HTTP GET`, `gRPC`, `SSE`, `WebSocket`, `SQL`, `AMQP publish`, `Kafka publish`, `docker exec`, `stdout`, `filesystem write`. One step, one transport. |
| `payload`   | string | route + key headers (auth, idempotency, content-type) + key body fields. NOT a generic "request body". |
| `note`      | string | optional; usually `src=<path>:<line>` citation or a one-line explanation. |
| `unknown`   | bool   | optional, default `false`. Set when the skill cannot confirm the step from a real source signal. |
| `reason`    | string | required iff `unknown:true`. Names the file or signal that would resolve it. |

### Citation rule

Every emitted step carries one of two permitted shapes:

1. **Cited:** `payload` or `note` contains a `file:line` token (`src=<path>:<line>` or `path/to/file.py:42`). The line points at the route handler, the queue subscription, the cron registration, or the actual call site.
2. **Unknown:** `unknown: true` AND `reason` is a sentence naming the file that would resolve it. Example: `"Would confirm from services/orders/app/payments.py:42 if readable."`

A step with neither shape is a fabrication. The skill rewrites it into the unknown shape before saving. There is no third permitted shape.

---

## Canonical example

Excerpt from [`examples/fastapi-starter/flows.json`](../examples/fastapi-starter/flows.json):

```json
{
  "units": [
    {
      "id": "client",
      "kind": "service",
      "label": "Client",
      "role": "External HTTP caller (curl, browser, or another service) posting orders."
    },
    {
      "id": "app",
      "kind": "service",
      "label": "FastAPI app",
      "role": "The application process; routes, dependencies, and the BackgroundTasks queue."
    },
    {
      "id": "db",
      "kind": "service",
      "label": "Postgres",
      "role": "Primary data store for the orders table and the schema migrations table."
    }
  ],
  "flows": [
    {
      "id": "create-order",
      "category": "user",
      "title": "Customer creates an order",
      "narration": "An external client POSTs an order to the FastAPI app, which inserts a row into Postgres and queues a background task before returning 201.",
      "steps": [
        {
          "from": "client",
          "to": "app",
          "transport": "HTTP POST",
          "payload": "POST /v1/orders body: {customer_id, amount_cents, currency}",
          "note": "src=app/routes/orders.py:24"
        },
        {
          "from": "app",
          "to": "db",
          "transport": "SQL",
          "payload": "INSERT INTO orders (id, customer_id, amount_cents, currency, status, created_at) VALUES (...)",
          "note": "src=app/routes/orders.py:48"
        }
      ]
    }
  ],
  "glossary": {
    "Idempotency key": "A client-supplied token that lets the server detect and reject duplicate requests.",
    "Background task": "A FastAPI feature that runs a coroutine after the response is flushed but inside the same process."
  }
}
```

---

## `glossary`

Free-form term to one-sentence definition. The renderer alphabetises. Hand-edits are preserved across re-runs keyed by term string.

```json
{
  "Idempotency key": "A client-supplied token that lets the server detect and reject duplicate requests.",
  "SSE": "Server-Sent Events; a one-way HTTP stream from server to client."
}
```

---

## Validation rules (what CI enforces)

The `validate-examples` job rejects a file that fails any of:

- Parses as JSON (`jq empty` returns 0).
- `flows[].category` is one of `user`, `internal`, `background`, `build`.
- Every `step.from` and `step.to` is in `units[].id`.
- No orphan units — every declared unit is referenced as `from` or `to` in at least one step.
- No banned phrase appears in any narration or payload or note (see [narration-style.md](../skills/codestory/references/narration-style.md)).

The `snapshot-counts` job additionally compares the file's flow / unit / step counts against `.github/snapshots/baseline.json` and fails on unexpected drift.

---

## Hand-edit preservation

The skill's re-run merge is keyed by:

- `flow.id` for flow-level fields (`title`, `narration`, `category`).
- `(flow.id, step.index)` for step-level fields.
- `unit.id` for unit-level fields.
- term string for glossary entries.

For every paired key in both the prior file and the regenerated file, if the prior value differs from the regenerated value, the prior value wins. Hand-edits to a narration survive every subsequent `/codestory` run.

Prior entries with no regenerated counterpart are kept and marked `stale:true` in a sibling `.codestory-meta.json`. The skill surfaces stale entries to the user; nothing is ever silently dropped.
