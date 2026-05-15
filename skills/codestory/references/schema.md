# `flows.json` v1 — field reference

This file documents every field the skill emits and every field a hand-edit may touch. Pair with SKILL.md §5 (re-run merge contract): hand-edits keyed by `(flow.id, step.index)` are preserved across re-runs.

## Top-level shape

```json
{
  "project_name": "cliproxyapi",
  "lead": "One-sentence project blurb shown under the home headline.",
  "actors":     { "<id>": { "label": "...", "tech": "..." }, ... },
  "units":      [ Unit, ... ],
  "categories": [ Category, ... ],
  "flows":      [ Flow, ... ],
  "glossary":   { "term": "definition", ... }
}
```

Seven top-level keys. The skill emits ALL of them.

- `project_name` — string. Shown in the page title (`<project> stories`) and the home header.
- `lead` — string, optional. One-sentence project blurb. The renderer falls back to its built-in lead if absent.
- `actors` — **object keyed by id** mapping `id` → `{ label, tech }`. This is the shape the renderer reads at runtime (`actors[step.from].label`). Every step's `from` and `to` MUST be a key here.
- `units` — array of `Unit` records (`{id, kind, label, role}`). The v1 / canonical form, kept for external tooling. The skill emits `units` AND `actors` together — same source data, two views. The renderer normalises automatically if only one is present, but emitting both is the contract.
- `categories` — array of `Category` records. One entry per distinct `flow.category` value actually used. The renderer draws home-page chapter cards from this list. If empty / missing, the renderer derives placeholders from `flow.category` values but the chapter titles and blurbs are then generic.
- `flows` — array of stories. Each flow is one runtime path through the system.
- `glossary` — object mapping a term to a one-sentence definition. The renderer turns these into a side panel.

### Why the actors / units duality

The renderer's JavaScript was lifted from a hand-authored medchat artefact and reads `actors` as an object. The skill's discovery output is more naturally an array of records (`units`). Rather than rewrite the renderer or constrain the skill, the contract is: emit both. The renderer normalises if only one shape arrives. See `SKILL.md` §3 for the canonical mirror example.

## `Category`

```json
{
  "id": "user",
  "title": "When a user does something",
  "blurb": "Routes that fire when a homelab service hits the gateway.",
  "mood": "default"
}
```

Fields:

- `id` — one of: `user`, `internal`, `background`, `build`. Matches `flow.category` values.
- `title` — chapter headline shown on the home page. Reads like a book chapter title.
- `blurb` — one or two sentences describing the chapter. Shown under the title.
- `mood` — optional rendering hint: `default`, `night`, `build`. Affects background tint for the chapter's scene panel.

## `Unit`

```json
{
  "id": "orders-api",
  "kind": "service",
  "label": "Orders API",
  "role": "Accepts order writes; emits domain events to the bus."
}
```

Fields:

- `id` — string, kebab-case, unique across the file. The stable key. Every step's `from` / `to` references this id.
- `kind` — one of: `service`, `package`, `app`, `module`. The renderer styles each kind with a different chip.
- `label` — string. Human-readable name shown in the diagram. Title Case.
- `role` — string. One sentence describing what the unit exists to do. Sets up the reader's mental model before the first flow.

## `Flow`

```json
{
  "id": "create-order",
  "category": "user",
  "title": "Customer creates an order",
  "narration": "Top-level summary; one to three sentences naming the trigger and the outcome.",
  "steps": [ Step, ... ]
}
```

Fields:

- `id` — string, kebab-case, unique across `flows[]`. The stable key for the re-run merge contract.
- `category` — one of exactly four chapters. The renderer groups flows by chapter.
- `title` — string. The story name displayed at the top of the scene panel. Reads like a chapter title.
- `narration` — string. Top-level summary of the whole flow; the long description of each step lives in the per-step fields.
- `steps` — array of `Step` objects in execution order.

### Categories (the four chapters)

Exactly four. The renderer enforces this; an unknown category fails validation.

- `user` — the trigger is a human action against a UI or public API. Sign-up, post a message, click a button.
- `internal` — the trigger is one service calling another service inside the system. Service-to-service RPC, queue producer to consumer.
- `background` — the trigger is a scheduler. Cron, Celery beat, Kubernetes CronJob, GitHub Actions schedule.
- `build` — the trigger is a developer action against the build / deploy surface. CI run, docker image build, database migration.

A flow lives in exactly one chapter, picked by the primary trigger.

## `Step`

```json
{
  "from": "orders-api",
  "to": "payments-api",
  "transport": "HTTP POST",
  "payload": "POST /v1/payments  Idempotency-Key=<order_id>  body: {amount, currency, source}",
  "note": "src=services/orders/app/payments.py:42",
  "viz": "hop",
  "screenshot": null,
  "unknown": false,
  "reason": null
}
```

Fields:

- `from` — string, must match a `Unit.id` declared in the file. The step's source.
- `to` — string, must match a `Unit.id`. The step's destination.
- `transport` — string, names the wire shape. Examples: `HTTP POST`, `HTTP GET`, `gRPC`, `SSE`, `WebSocket`, `SQL`, `AMQP publish`, `Kafka publish`, `docker exec`, `stdout`, `filesystem write`. One step, one transport.
- `payload` — string, specific. Names the route or topic, the key headers (auth, idempotency, content-type), the key body fields. NOT a generic "request body".
- `note` — string, optional. Free-text annotation. Typically used for the `file:line` citation (`src=path/to/file.py:42`) or a one-line explanation of a non-obvious choice.
- `viz` — string, optional. Names the renderer to draw this step. One of `hop` (default cross-actor packet), `self` (loop back to source), `queue`, `broadcast`, `notification`, `db-write`, `db-read`, `pipeline`, `state`, `screenshot`. The renderer picks `hop` / `self` automatically when `viz` is absent; for the other shapes the skill MUST emit `viz` explicitly so the renderer does not fall back to a generic packet animation. `viz_type` is accepted as an alias for backward compatibility.
- `screenshot` — string, optional. A data URI or relative path to an image of the affected UI for this step. When present, the renderer uses the `screenshot` viz unless `viz` is set to something else. Captured by the opt-in `codestory.run` flow (see SKILL.md §8.5).
- `screenshotUrl` / `url` — string, optional. The URL shown in the mocked browser chrome above the screenshot.
- `unknown` — bool, optional, default `false`. Set to `true` when the skill cannot confirm the step from a real source signal.
- `reason` — string, required iff `unknown:true`. Names the file or signal that would resolve the unknown. Example: `"Would confirm from services/orders/app/payments.py if readable."`

### Picking `viz` (chooser heuristic)

Default behaviour (renderer fallback when `viz` is absent): `hop` if `from !== to`, `self` if `from === to`. The skill SHOULD set `viz` explicitly when the step matches one of the shapes below — otherwise every step renders as a packet-on-arc and the user sees the same animation N times per flow.

| `viz`          | When to pick it                                                                                              |
|----------------|--------------------------------------------------------------------------------------------------------------|
| `queue`        | Transport names a queue / pub-sub / stream. Words: queue, celery, kafka, rabbit, sqs, topic, publish, consume |
| `broadcast`    | One sender, fan-out to many receivers. WebSocket broadcast, SSE-to-all, notify-all                            |
| `notification` | Webhook, email, SMS, push notification — fire-and-forget side channels                                        |
| `db-write`     | Insert / update / upsert / delete against a datastore                                                         |
| `db-read`      | Select / fetch / query against a datastore                                                                   |
| `pipeline`     | Build / transform / compile chain (typically in the `build` chapter)                                           |
| `state`        | State machine transition. Payload reads like `"draft" → "submitted"` or `status: new → confirmed`              |
| `screenshot`   | UI step where the captured image is the point. Set automatically when `screenshot` field is present           |
| `self`         | `from === to` (set automatically, but may be overridden)                                                       |
| `hop`          | Anything else / cross-actor RPC. Default                                                                     |

The renderer accepts unknown `viz` values by falling back to `hop`; consumers should not crash on a new viz type.

### Hard rule on citations

Every emitted step MUST carry a citation. The skill is forbidden from emitting a step without one. The two permitted shapes are:

1. **Cited step:** `note` (or `payload`) contains a `file:line` token in the form `src=<path>:<line>` (or `path/to/file.py:42` — any form a reader can grep for). The line points at the route handler, the queue subscription, the cron registration, the call site, or whichever source signal led the skill to emit the step.
2. **Unknown step:** `unknown:true` AND `reason` names the file or signal that would resolve it. The reason is a sentence, not a placeholder.

A step lacking both shapes is a fabrication and MUST NOT be saved. The skill rewrites the step into the unknown shape before saving.

## Hand-edit preservation contract

The skill MUST preserve hand-edits across re-runs. See SKILL.md §5 for the full algorithm.

Summary of the contract:

- The merge key is `(flow.id, step.index)` for steps; `flow.id` for flow-level fields (`title`, `narration`, `category`); `unit.id` for unit-level fields; the term string for glossary entries.
- For every paired key present in both the prior file and the regenerated data, the merge compares each field. If the prior value differs from the regenerated value, the prior value is treated as a hand-edit and preserved.
- New entries from the regenerated run that have no prior key are appended.
- Prior entries with no regenerated counterpart are kept; they are marked `stale:true` in a sibling `.codestory-meta.json` and surfaced to the user, never silently dropped.

A user who edits a narration once should never see that edit overwritten by a later `/codestory` run.

## `glossary`

```json
{
  "Idempotency key": "A client-supplied token that lets the server detect and reject duplicate requests.",
  "SSE": "Server-Sent Events; a one-way HTTP stream from server to client."
}
```

Free-form term → one-sentence definition. The renderer alphabetises. Hand-edits to glossary entries are preserved by term string.

## Validation summary

The skill rejects a file that fails any of the following (see SKILL.md §9 R11 for the runtime guard):

- `project_name` is a non-empty string.
- `actors` is a non-empty object keyed by id; `units` is a non-empty array. Both required; they mirror the same data.
- `categories` is a non-empty array with one entry per distinct `flow.category` value present.
- `flows` is a non-empty array. Every `flow.id` unique. Every `flow.category` is one of `user`, `internal`, `background`, `build`. Every flow has `id`, `name`, `category`, `narration`, `steps`.
- Every `step` has `from`, `to`, `transport`, `payload`. Every `step.from` and `step.to` references a key in `actors`.
- Every step is either cited (carries a `file:line` token in `note` or `payload`) or marked `unknown:true` with a non-empty `reason`.
- No banned phrase appears in any `flow.narration`, `step.payload`, or `step.note` (see `references/narration-style.md`).
