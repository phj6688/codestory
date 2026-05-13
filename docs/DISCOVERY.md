# Discovery — the seven-step playbook

This is how the `codestory` skill turns a repository into a `flows.json`. The playbook is a discipline, not a heuristic: each step is enforced by the skill at runtime and by CI at every PR.

This document is written for human readers — someone editing a `flows.json` by hand, reviewing a generated one, or auditing the skill's output. The terse runtime version lives at [`skills/codestory/SKILL.md`](../skills/codestory/SKILL.md).

---

## The seven steps

### 1. Pick a unit kind

The unit kind is the granularity of the book. The skill chooses one of four, and states the choice explicitly in the output:

- **`services`** — independently deployable processes. FastAPI apps, Celery workers, Next.js apps, Django apps.
- **`packages`** — Python wheels, npm packages, Go modules. Useful when one repo ships a library plus its consumer.
- **`apps`** — top-level applications inside a monorepo. Apps in `apps/` directories, often with their own `package.json`.
- **`modules`** — domain modules inside a single application. Useful when one service is large enough that its internals merit a flow book of their own.

The choice is binding for the whole `flows.json`. In [`examples/fastapi-starter`](../examples/fastapi-starter/flows.json) the unit kind is `services` because there are four deployable surfaces: the client, the FastAPI app, Postgres, and the SMTP relay. In [`examples/django-celery`](../examples/django-celery/flows.json) the kind is `services` again because the worker, the beat scheduler, the Django app, the broker, and the database all sit at the same deployment boundary.

### 2. Enumerate flows from real signals

A flow exists when a real source signal in the codebase triggers a runtime path. The signals the skill looks for:

- HTTP routes — decorators, route registrations, OpenAPI generators.
- Queue consumers — Celery tasks, RabbitMQ handlers, Kafka subscribers.
- Scheduled jobs — cron registrations, Celery beat schedules, GitHub Actions schedules.
- CLI entrypoints — `argparse` parsers, `click` commands, `bin/` scripts.
- Webhook receivers — explicit route handlers tagged as inbound webhooks.
- UI buttons / form submits — only when their handler is visible in the codebase.
- Build and deploy — `docker-compose.yml` services, `Dockerfile` build stages, CI workflows.

A signal the skill cannot resolve does NOT become a flow. It becomes an `unknown:true` step with a `reason` field naming the file that would confirm it. **The skill is forbidden from inventing flows.**

In [`examples/medchat`](../examples/medchat/flows.json), 18 flows are emitted because 18 real signals exist across HTTP routes, SSE streams, and Celery tasks. In [`examples/fastapi-starter`](../examples/fastapi-starter/flows.json), three flows surface: the user-triggered `POST /v1/orders`, the FastAPI `BackgroundTasks` receipt task, and the Alembic migration on startup.

### 3. Step shapes per the schema

Each step is one record:

```json
{
  "from":      "<unit-id>",
  "to":        "<unit-id>",
  "transport": "<wire-shape>",
  "payload":   "<route + headers + key body fields>",
  "note":      "src=<path>:<line>"
}
```

`from` and `to` are real unit ids declared in `units[]`. `transport` names the wire — `HTTP POST`, `SQL`, `SSE`, `AMQP publish`, `docker exec`, and so on. `payload` is specific: the route or topic, the key headers (`Authorization`, `Idempotency-Key`, `Content-Type`), the key body fields. **A payload that reads "request body" is failing the contract.** `note` carries the `file:line` citation; without one, the step is `unknown:true`.

See [`docs/SCHEMA.md`](./SCHEMA.md) for the full field reference.

### 4. Narration writing

Narration is prose. The voice contract is in [`skills/codestory/references/narration-style.md`](../skills/codestory/references/narration-style.md). The rules:

- Active voice, subject-verb-object. "The API writes the row." Not "A row is written."
- Complete sentences only. No fragments.
- Define jargon on first use within a flow.
- Connect cause and effect across sentences explicitly.
- Soft cap of 60 words per step.
- Markup unit names with `<span class="who">` and identifiers (routes, function names, env vars, tables, topics) with `<span class="what">`.

The banned-phrase list is enforced before save. `handles`, `manages`, `deals with`, `communicates with`, `leverages`, `robust`, `gracefully`, `for clarity`, `this ensures`, `straightforward` — each is replaced with a specific verb or mechanism. Examples and rationale in the narration-style file.

In [`examples/nextjs-starter`](../examples/nextjs-starter/flows.json), the `purchase-checkout` flow narration names the exact route segment (`POST /api/checkout/session`) and the precise Stripe call (`stripe.checkout.sessions.create`) — concrete identifiers, no filler.

### 5. Categorise into one of four chapters

Every flow lives in exactly one chapter. The choice is made by **primary trigger**:

- `user` — a human action against a UI or public API. The customer POSTs an order. A logged-in user clicks "Send".
- `internal` — one service calls another inside the system. A queue consumer fires. A scheduled job re-enqueues work.
- `background` — a scheduler triggers the work. Celery beat, Kubernetes CronJob, cron, GitHub Actions schedule.
- `build` — a developer action against the build / deploy surface. CI runs, image builds, migrations applied on startup.

In [`examples/django-celery`](../examples/django-celery/flows.json), `nightly-report` lives in `background` because the trigger is Celery beat. The `startup-migration` flow in [`examples/fastapi-starter`](../examples/fastapi-starter/flows.json) lives in `build` because the trigger is the developer running `docker compose up` and the FastAPI startup event applying Alembic.

The CI `validate-examples` job rejects any other value. The renderer groups flows into four panels — no flow without a chapter renders.

### 6. Coverage check

Before any HTML is written, the skill surfaces three things to the user:

- **`unknown:true` count** — how many emitted steps are marked unknown, listed by flow id + step index.
- **Orphan unit list** — every unit declared in `units[]` that is never referenced as `from` or `to` in any step.
- **Total flow count** — across all chapters.

If the flow count is 30 or more, the skill **stops** and prompts the user with a split-or-filter decision: narrow with `--scope user|internal|background|build`, or partition by service. This is the R7 mitigation — a 50-flow monorepo never silently turns into a 12-flow HTML. The medchat example sits at 18 flows; that's the largest book that ships as a single render in this repo.

### 7. Reading budget

Three passes, capped:

- **Pass 1 — top-level scan.** 30 files max, depth 2 from the working directory. Reads `pyproject.toml`, `package.json`, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, top-level `README.md`, top two directory levels. Output: candidate unit kinds.
- **Pass 2 — per-unit entrypoint.** 5 files per unit. Reads `main.py` / `app.py` / `index.ts` / `server.ts`, the routes file, the worker file, the CLI entrypoint, the unit's README. Output: real source signals with `file:line`.
- **Pass 3 — per-flow call-site verify.** 3 files per flow. Reads the entrypoint file plus up to two call-site files. Output: cited steps; anything not resolvable becomes `unknown:true`.

Soft total: 200 file reads per `/codestory` run. When the budget approaches, the skill surfaces a budget-exhausted notice with a recommended `--scope` narrowing.

The skill does NOT read: the whole codebase, test files (unless the only entrypoint signal lives in one), `node_modules`, `.venv`, `site-packages`, `dist`, `build`, binary files, anything outside the working directory.

---

## Common pitfalls

The three failure modes the skill watches at runtime, in order of how often they cause real damage.

### Invented flows

Symptom: a flow appears in the output that doesn't correspond to any real source signal. The skill imagined it from a README sentence or a comment.

Why it happens: code-reading LLMs default to plausible completion when a signal is partial. Without the citation rule, "the orders service sends an email" can turn into a fully-fleshed step that doesn't exist in the codebase.

Mitigation: every step carries `src=<path>:<line>` in `payload` or `note`. If the skill cannot supply one, the step is `unknown:true` with a `reason` naming the file that would resolve it. The pre-save check rewrites un-cited steps into the unknown shape before write. **There is no third permitted shape.**

How to spot in review: grep `note` and `payload` for `src=`. Any step without a citation token AND without `unknown:true` is a fabrication.

### Banned phrases

Symptom: a narration reads "the worker gracefully handles retries" or "this ensures idempotency". The voice goes generic; the reader learns nothing about the actual mechanism.

Why it happens: the banned-phrase list catches every filler word LLMs reach for under uncertainty. `handles`, `manages`, `deals with` hide the verb. `robust`, `gracefully` make claims without content. `for clarity`, `this ensures` announce explanations instead of giving them.

Mitigation: the skill greps every narration / payload / note string against the banned list before save. On hit, it rewrites — bounded to three passes per string. If the rewrite loop fails to converge, the skill stops and asks the user. The full list and rationale are in [`skills/codestory/references/narration-style.md`](../skills/codestory/references/narration-style.md).

How to spot in review: `git grep -i -E "(handles|manages|deals with|communicates with|leverages|robust|gracefully|for clarity|this ensures|straightforward)" examples/*/flows.json`. The CI `lint-skill` job runs the same grep against the shipped skill text.

### Orphan units

Symptom: `units[]` declares an SMTP relay or a third-party API, but no step actually references it. The diagram shows a node nothing connects to.

Why it happens: the skill listed every plausible unit during pass 1 but the call-site verify in pass 3 never produced a step using it. The unit is dead weight in the JSON and a misleading node in the SVG.

Mitigation: the coverage check (step 6) surfaces orphan unit ids to the user before write. Either a flow that uses the unit gets added (with citation), or the unit gets removed from `units[]`.

How to spot in review: for each `unit.id`, search `flows[].steps[]` for any step where `from == id || to == id`. CI's `validate-examples` job rejects orphan units.
