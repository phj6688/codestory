---
name: codestory
description: Turn any codebase into a beautifully animated book of workflows. Single HTML file.
---

# codestory skill

This skill turns a repository into one self-contained animated HTML file: a book of workflows with four chapters (`user`, `internal`, `background`, `build`). The skill activates from the `/codestory` slash command, reads the repository under a strict three-pass budget, emits a `flows.json` v1 data block, and pipes that through the bundled renderer with one of four themes.

The skill is opinionated. Every step it emits cites a real source signal. Every narration string passes a pre-save banned-phrase check. Every re-run preserves user hand-edits keyed by `(flow.id, step.index)`. Every run reports its coverage before writing.

The rest of this file is the runtime contract. Reference docs in `skills/codestory/references/` carry the details the runtime consults: `schema.md` for the JSON shape, `narration-style.md` for the voice rules and the banned-phrase list, `trigger-rules.md` for invocation and flag parsing.

---

## 1. Activation

The skill activates when the user invokes the `/codestory` slash command in a session where the codestory plugin is installed. Full conditions, flag list, and stop conditions live in `references/trigger-rules.md`.

Three load-bearing facts to keep in mind at activation:

- The working directory at invocation time becomes the discovery root. The skill reads only inside it unless a flag points elsewhere.
- The bundled renderer assets live at `renderer/template.html` and `renderer/themes/*.css` inside the plugin install directory. The skill reads them at render time; it does not copy them into the user's repo.
- A prior `codestory.html` or `codestory.json` in the working directory is treated as the source of hand-edits and merged in. The skill does NOT clobber it.

### Activation step 0 — resolve the theme before any discovery work

The very first thing the skill does, before reading a single source file, is resolve which theme to render with. Resolution order (first match wins):

1. `--theme <name>` or `--theme <path>` on the slash command.
2. Repo manifest: `package.json` `"codestory": { "theme": "<name>" }` or `pyproject.toml` `[tool.codestory] theme = "<name>"`.
3. **Interactive prompt to the user** (default path). The skill MUST ask, not silently fall back to `cococream`. The prompt is:

   ```
   Which theme would you like?
     1) cococream         (default, warm paper)
     2) dark              (near-black, amber accent)
     3) minimal           (mono, print-friendly)
     4) nothing-design    (OLED, red interrupt)

   Enter number or name:
   ```

   Accepts: `1`, `2`, `3`, `4`, or any of the four names case-insensitive, or empty input to take the printed default `cococream`. On any other input, re-prompt once with the same options; on a second bad input, abort discovery with a one-line error naming the four valid choices.

4. `cococream` silently — only when the slash-command form was `/codestory --no-prompt` or when running in a non-interactive context (no user channel available). The skill records the silent fallback in the discovery summary.

The chosen theme is recorded immediately and passed to the renderer at output time (§8). Theme choice does not change discovery — same flows, same units, same JSON; only the CSS injection differs.

---

## 2. The seven-step discovery playbook

Transcribed verbatim from TASKSPEC §6. No deviation, no reordering.

1. Pick a unit kind (`services` / `packages` / `apps` / `modules`) — stated explicitly in output
2. Enumerate flows from real signals (HTTP routes, queue consumers, scheduled jobs, CLI entrypoints, webhook receivers, UI buttons, build/deploy)
3. Step shapes per §4 above
4. Narration writing per `references/narration-style.md` (active voice, complete sentences, banned-phrase list, `<span class="who|what">` markup)
5. Categorise into exactly one of four chapters by primary trigger
6. Coverage check: every from/to references a real unit, orphans listed, `unknown:true` count surfaced, 30+ flows prompts split-or-filter decision
7. Reading budget: three passes (top-level scan / per-unit entrypoint / per-flow call-site verify); never reads whole codebase

Below is one concrete example per step, drawn from a small synthetic FastAPI project. The project has three services: `orders-api` (a FastAPI app), `payments-api` (a FastAPI app), and `orders-worker` (a Celery worker). The DB is PostgreSQL.

### Example walkthrough

The example project tree:

```text
synthetic-orders/
├── services/
│   ├── orders/
│   │   └── app/
│   │       ├── main.py        # FastAPI app, route definitions
│   │       ├── payments.py    # outbound call to payments-api
│   │       └── tasks.py       # Celery task definitions
│   └── payments/
│       └── app/
│           └── main.py        # FastAPI app, route definitions
├── docker-compose.yml
└── pyproject.toml
```

**Step 1 — pick unit kind.**

The skill scans the top-level layout and reads `pyproject.toml`. It finds three deployable surfaces under `services/`, each with its own FastAPI or Celery entrypoint. The unit kind is `services`. The skill records this choice in the output and prints it to the user: `unit kind: services (3 found)`.

**Step 2 — enumerate flows from real signals.**

The skill reads each unit's entrypoint and collects the real source signals:

- `services/orders/app/main.py:14` → `@app.post("/v1/orders")` → user-triggered flow `create-order`.
- `services/orders/app/main.py:42` → `@app.get("/v1/orders/{id}")` → user-triggered flow `read-order`.
- `services/orders/app/tasks.py:8` → `@app.task(name="orders.confirm")` → internal flow triggered from the order-create path.
- `services/payments/app/main.py:11` → `@app.post("/v1/payments")` → internal flow `charge-payment`, called by orders-api.

Each signal is a real file:line. The skill records the citation alongside the flow it suggests. A signal the skill cannot resolve (a route handler that imports a module the skill did not read) is not turned into an emitted flow; it becomes an `unknown:true` step with a `reason` pointing at the file that would resolve it.

**Step 3 — step shape per `references/schema.md`.**

For `create-order`, the skill emits one step like this:

```json
{
  "from": "orders-api",
  "to": "payments-api",
  "transport": "HTTP POST",
  "payload": "POST /v1/payments  Idempotency-Key=<order_id>  body: {amount, currency, source}",
  "note": "src=services/orders/app/payments.py:42"
}
```

`from` and `to` are real unit ids declared in `units[]`. `transport` names the wire shape. `payload` names the route, the key header (idempotency key), and the key body fields. `note` carries the `file:line` citation that justified this step's existence.

**Step 4 — narration per `references/narration-style.md`.**

The narration for the same step:

> `<span class="who">orders-api</span>` calls `<span class="what">POST /v1/payments</span>` on `<span class="who">payments-api</span>` with an idempotency key derived from the order id. The payments service rejects a duplicate idempotency key with `<span class="what">409 Conflict</span>`, which `<span class="who">orders-api</span>` catches and treats as a no-op so the retry path stays safe.

Active voice. Subject-verb-object. Banned phrases absent. Markup spans wrap the unit names and the identifiers. Cause and effect connect across sentences. The sentence count is two, well under the 60-word soft cap.

**Step 5 — categorise into one of four chapters.**

The primary trigger for `create-order` is a customer POST against the public API: chapter is `user`. The primary trigger for `orders.confirm` is the Celery worker consuming a queue message: chapter is `internal`. The primary trigger for a hypothetical `nightly-recon` cron is the scheduler: chapter is `background`. The primary trigger for a `docker compose build` flow is the developer at the CLI: chapter is `build`. A flow lives in exactly one chapter.

**Step 6 — coverage check.**

After enumerating, the skill reports:

```text
units: 3 declared, 3 referenced, 0 orphan
flows: 4 emitted, 0 unknown
banned-phrase pre-save grep: clean
```

Orphan units (declared in `units[]` but never referenced as `from` or `to` in any step) are listed by id. Unknown steps (`unknown:true`) are counted and listed by flow id. The user sees this report before any file is written. On a 30+ flow run, the skill stops here and prompts the user for a `--scope` filter or a split.

**Step 7 — reading budget.**

For this small project the skill read 4 entrypoint files in pass 2 and 2 call-site files in pass 3, well under the per-pass caps. On a real monorepo the budget binds; see §7 below for the explicit caps.

---

## 3. Step shape contract

The full field reference lives in `references/schema.md`. The runtime contract for the skill is:

A step is one record with these fields: `from`, `to`, `transport`, `payload`, optional `note`, optional `unknown`, optional `reason`.

### Output JSON shape — canonical example (copy this skeleton, do not invent fields)

The skill writes a single `flows.json` (embedded inside `<script id="codestory-data">` in the HTML, unless `--split` is used). The renderer reads specific keys; emitting different keys produces a broken render that looks like a static demo. The skill MUST emit this exact top-level shape:

```json
{
  "project_name": "cliproxyapi",
  "lead": "OpenAI-compatible gateway routing chat completions to local Ollama and remote Claude over OAuth.",
  "actors": {
    "client": { "label": "Client", "tech": "homelab service on the tailnet" },
    "gateway": { "label": "Gateway", "tech": "FastAPI :18789" },
    "ollama": { "label": "Ollama", "tech": "local model server :11434" }
  },
  "units": [
    { "id": "client",  "kind": "service", "label": "Client",  "role": "homelab service on the tailnet" },
    { "id": "gateway", "kind": "service", "label": "Gateway", "role": "FastAPI :18789" },
    { "id": "ollama",  "kind": "service", "label": "Ollama",  "role": "local model server :11434" }
  ],
  "categories": [
    { "id": "user",       "title": "When a user does something",  "blurb": "Routes that fire when a homelab service hits the gateway.", "mood": "default" },
    { "id": "internal",   "title": "Behind the scenes",            "blurb": "Internal routing, alias resolution, streaming.",            "mood": "default" },
    { "id": "background", "title": "Scheduled jobs",               "blurb": "Token refresh, container watchdog.",                        "mood": "night"   },
    { "id": "build",      "title": "Deploy and setup",             "blurb": "Container boot, OAuth onboarding.",                         "mood": "build"   }
  ],
  "flows": [
    {
      "id": "chat-completion",
      "name": "Chat completion request",
      "title": "Chat completion request",
      "category": "user",
      "color": "var(--accent)",
      "trigger": "POST /v1/chat/completions",
      "narration": "A homelab service posts an OpenAI-style chat request to the gateway. The gateway validates the bearer token, resolves the model alias, and streams the response from the upstream provider.",
      "steps": [
        {
          "from": "client",
          "to": "gateway",
          "transport": "HTTP POST /v1/chat/completions",
          "payload": "Authorization: Bearer; body: { model, messages, stream } — src=config.yaml:8",
          "note": "host: \"\" and port: 18789 in config bind the listener inside the container.",
          "viz": "hop",
          "unknown": false
        }
      ],
      "glossary_refs": ["bearer", "model-alias"]
    }
  ],
  "glossary": {
    "bearer": "An opaque token in the Authorization header that authenticates the caller.",
    "model-alias": "A string in the request body the gateway maps to an upstream provider."
  }
}
```

**Mirror keys — both forms MUST be emitted** so the renderer and any v1-aware consumer both work:

- `actors` (object keyed by id, values `{label, tech}`) AND `units` (array of `{id, kind, label, role}`). Same source data, two views.
- Each flow gets `name` AND `title` (same string). The renderer uses `name`; v1 consumers use `title`.

**Required keys — empty or missing means the render breaks:**

- `project_name` — non-empty string. Drives the page title and header.
- `actors` — non-empty object. Every step's `from` and `to` MUST be a key in `actors`.
- `categories` — non-empty array with one entry per distinct value of `flow.category` actually used. The id must be one of `user`, `internal`, `background`, `build`. The `title` is the chapter headline shown on the home page; the `blurb` is the chapter description.
- `flows[]` — non-empty array. Each flow has `id`, `name`, `category`, `narration`, `steps[]`.
- Each `step` — `from`, `to`, `transport`, `payload` minimum. `note` optional. `unknown` only when the citation rule forces it (see Hard rule below). `viz` optional — see §3.1 below; absent means the renderer picks `hop` / `self` automatically.

**Forbidden top-level keys:** `meta`, `lineRef`, `body`, `label`, `title` at the step level. These were the shapes the skill hallucinated in an early CLIproxyAPI run and are not part of the contract. The renderer ignores them.

### Hard rule on citations

This is the R1 mitigation. It is not a guideline. The skill enforces it before write.

**Every step the skill emits MUST cite `file:line` in the `payload` or `note` field. If the skill cannot supply a citation, the step is `unknown:true` with a `reason` field naming the file that would confirm it.**

Two permitted shapes:

1. **Cited step.** Either `payload` or `note` contains a citation token in the form `src=<path>:<line>` (or any path:line pattern a grep can find). The line points at the route handler, the queue subscription, the cron registration, the call site, or whichever real signal led the skill to emit this step.
2. **Unknown step.** `unknown:true` AND `reason` is a sentence naming the file or signal that would resolve it. Example: `"Would confirm from services/orders/app/payments.py:42 if readable."`

A step that lacks both shapes is a fabrication. The skill rewrites it into the unknown shape before saving. There is no third permitted shape.

### 3.1 Picking `viz` (the per-step visualizer)

Every step renders into a scene. The renderer ships ten visualizers; the skill picks the one that matches the step's shape so the user does not watch the same packet-on-arc animation N times per flow.

The renderer auto-picks `hop` (cross-actor) or `self` (`from === to`) when `viz` is absent. For the other shapes, the skill MUST set `viz` explicitly:

| `viz`          | When to pick it                                                                                              |
|----------------|--------------------------------------------------------------------------------------------------------------|
| `queue`        | Transport names a queue / pub-sub / stream: queue, celery, kafka, rabbit, sqs, redis pub/sub, AMQP topic     |
| `broadcast`    | One sender, fan-out to many receivers. WebSocket broadcast, SSE-to-all, notify-all                            |
| `notification` | Webhook, email, SMS, push notification — fire-and-forget side channels                                        |
| `db-write`     | Insert / update / upsert / delete against a datastore (sql, mongo, redis-as-store)                            |
| `db-read`      | Select / fetch / query against a datastore                                                                   |
| `pipeline`     | Build / transform / compile chain; almost always `flow.category === "build"`                                  |
| `state`        | State machine transition. Payload reads like `"draft" → "submitted"` or `status: new → confirmed`              |
| `screenshot`   | UI step where the captured image is the point. Set automatically when `step.screenshot` is non-empty           |
| `self`         | `from === to`. Set automatically; the skill may override with another viz where useful                         |
| `hop`          | Anything else / cross-actor RPC. Default                                                                     |

The skill does not invent new viz values. The renderer falls back to `hop` on an unknown viz, so a typo silently renders as a default packet animation instead of crashing. Run-time count: a healthy flow with N≥3 steps should use at least two distinct viz values; a flow that has all steps with the same viz is a signal that the skill should re-read the steps and pick more accurately.

The pre-save check (run after step 6, before write):

```python
for flow in flows:
    for i, step in enumerate(flow["steps"]):
        cited = re.search(r"\S+\.\w+:\d+", step.get("payload","") + " " + step.get("note",""))
        if cited:
            continue
        if step.get("unknown") and step.get("reason"):
            continue
        # rewrite: turn into unknown step
        step["unknown"] = True
        step["reason"] = step.get("reason") or f"No source citation collected for {flow['id']} step {i}."
```

---

## 4. Narration style

The voice contract is in `references/narration-style.md`. That file declares the banned-phrase list. This skill's runtime job is to enforce it.

### Mandate: one language per render

Every `flow.narration`, `step.payload`, `step.note`, `flow.title`, and `flow.name` in a single output file MUST be written in **one** language. The default is English. The user opts in to a different language at the top of the run, never per-string:

1. `--lang <code>` flag on the slash command (e.g. `--lang de`, `--lang fa`, `--lang en`).
2. Repo manifest: `package.json` `"codestory": { "lang": "<code>" }` or `pyproject.toml` `[tool.codestory] lang = "<code>"`.
3. Silent default: `en`.

Mixed-language narrations (English next to German next to Farsi inside one HTML) are the most common scar in the field — they happen when the model rewrites a string without remembering the prior language pin. The skill MUST treat them as a save-blocking error, not a stylistic preference.

**Pre-save language guard.** Before write, the skill samples every narration / payload / note string and flags any string whose dominant language differs from the run's chosen language. A trivial check is sufficient: run a script that counts characters in language-specific Unicode blocks (Latin-extended/A for German umlauts, Arabic for Farsi, CJK for Chinese, Cyrillic for Russian) plus a small high-frequency stopword grep (English: `the|and|of|to|with|for|when|that`; German: `der|die|das|und|nicht|mit|für|wird|ist`; Farsi: `که|این|آن|است|می|را`). Strings that score for a language other than the run's chosen one are rewritten before save, bounded to three passes per string. On non-convergence, the skill stops and asks the user to confirm the language pin.

Banned-phrase grep (below) runs over the rewritten strings, not the originals — language rewrites do not get a free pass on banned phrases.

### Mandate: pre-save banned-phrase grep, rewrite-before-save

This is the R4 mitigation.

**Before saving the JSON, the skill greps narration text for the banned-phrase list. On hit, the skill rewrites the offending narration and re-checks. The skill does not save until the grep is clean.**

The check covers every `flow.narration`, every `step.payload`, and every `step.note`. The grep is case-insensitive and word-boundary aware; see the actual regex used by the CI lint job for the exact word-boundary rules.

The rewrite is mandatory and on-skill — the skill does not save the file with a banned phrase and a note saying "TODO rewrite". Convergence is bounded at three passes per string; if a string still hits after three rewrites, the skill stops and asks the user to clarify the underlying behaviour.

The banned list (verbatim from TASKSPEC §9) lives in `references/narration-style.md`. The skill reads the list from that file at run time so the canonical declaration stays in one place.

---

## 5. Re-run merge contract

This is the R2 mitigation. The contract is exhaustive and binding.

### The hard rule

**The merge is keyed by `(flow.id, step.index)`. For each `(flow.id, step.index)` pair present in both the prior JSON and the regenerated JSON, the skill compares each field. If the prior value differs from the regenerated value, the prior value is treated as a hand-edit and is preserved in the merged output.**

Field-by-field, paired-key, prior-wins-on-diff.

### Algorithm

```text
load prior JSON from codestory.html (or codestory.json if --split)
run discovery → regenerated JSON

# units
for u_new in regenerated.units:
    u_old = prior.units.find(id == u_new.id)
    if u_old:
        for field in (kind, label, role):
            if u_old[field] != u_new[field]:
                u_new[field] = u_old[field]  # preserve hand-edit
    merged.units.append(u_new)
for u_old in prior.units:
    if not regenerated.units.find(id == u_old.id):
        merged.units.append(u_old)
        meta.stale_units.append(u_old.id)

# flows
for f_new in regenerated.flows:
    f_old = prior.flows.find(id == f_new.id)
    if f_old:
        for field in (category, title, narration):
            if f_old[field] != f_new[field]:
                f_new[field] = f_old[field]
        for i, s_new in enumerate(f_new.steps):
            s_old = f_old.steps[i] if i < len(f_old.steps) else None
            if s_old:
                for field in (from, to, transport, payload, note, unknown, reason):
                    if s_old.get(field) != s_new.get(field):
                        s_new[field] = s_old.get(field)
    merged.flows.append(f_new)
for f_old in prior.flows:
    if not regenerated.flows.find(id == f_old.id):
        merged.flows.append(f_old)
        meta.stale_flows.append(f_old.id)

# glossary
for term, defn in prior.glossary.items():
    if term in regenerated.glossary and regenerated.glossary[term] != defn:
        regenerated.glossary[term] = defn  # preserve hand-edit
merged.glossary = regenerated.glossary | {t: d for t, d in prior.glossary.items() if t not in regenerated.glossary}

write merged → codestory.html
write meta → .codestory-meta.json
```

### Stale entries

A prior entry with no regenerated counterpart is kept in the merged output AND recorded in `.codestory-meta.json` as `stale:true` with the prior id. The skill prints the stale list to the user after every run, so a deleted unit or a renamed flow never silently drops a user hand-edit.

### What counts as a hand-edit

Any difference between the prior file's field value and the freshly regenerated field value, for any field listed above. The skill makes no further distinction; user edits and skill regressions look identical, and prior-wins is the safer policy.

---

## 6. Coverage check

This is the R7 mitigation.

After step 6 of the discovery playbook (and before any write), the skill MUST surface two numbers and one list to the user:

- **`unknown:true` count.** How many emitted steps are marked unknown. Each one is listed with its flow id and step index.
- **Orphan unit list.** Every unit declared in `units[]` that is not referenced as `from` or `to` in any step.
- **Flow count.** Total flows enumerated.

The surface is text printed back to the chat before the HTML write happens. The user sees the numbers and either approves the write or course-corrects.

### 30+ flow case

When the flow count is 30 or more, the skill does NOT write the HTML on the first run. It stops with a split-or-filter prompt. Two paths forward:

1. **Filter:** the user re-invokes with `--scope <category>` to restrict to one chapter. Each chapter renders to its own HTML.
2. **Split:** the user names a chapter axis or a unit axis to partition by; the skill emits one HTML per partition.

The point is that a 50-flow monorepo never silently turns into a 12-flow HTML. The user is forced to confirm intent.

---

## 7. Reading budget

This is the R9 mitigation. The budget is enforced by three explicit per-pass caps and one soft total.

### Three passes

- **Pass 1 — top-level scan.** Cap: 30 files, depth 2 from the working directory. Reads: `pyproject.toml`, `package.json`, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, top-level `README.md`, and the top two directory levels. Output: candidate unit kinds and candidate unit ids.

- **Pass 2 — per-unit entrypoint.** Cap: 5 files per unit. Reads: the main file (e.g. `main.py`, `app.py`, `index.ts`, `server.ts`), the routes / views file, the worker / consumer file, the CLI / entrypoint file, the unit's own README. Output: real source signals (HTTP routes, queue consumers, scheduled jobs, CLI entrypoints, webhook receivers, UI buttons, build/deploy hooks).

- **Pass 3 — per-flow call-site verify.** Cap: 3 files per flow. Reads: the source file the flow's entrypoint signal lives in, plus up to two files the flow's call sites point at (e.g. the outbound client module, the queue publisher module). Output: cited steps. Anything Pass 3 cannot resolve becomes `unknown:true`.

### Soft total

**The soft total across all three passes is 200 file reads per `/codestory` run.** When the running total approaches the cap, the skill stops further discovery, emits what it has, and surfaces a budget-exhausted notice to the user with a recommended `--scope` narrowing.

### What the skill does NOT do

- Read the entire codebase. Greedy reads are the failure mode.
- Read test files unless the only entrypoint signal lives in one (rare).
- Read vendor and build directories: `node_modules/`, `.venv/`, `venv/`, `site-packages/`, `dist/`, `build/`, `.next/`, `target/`.
- Read backup, swap, and old-revision files: `*.bak`, `*.backup`, `*.orig`, `*~`, `*.swp`, `*.old`, `*.pre-*`, anything matching `*-pre-*` or `*.pre[-.]*`.
- Read binary files.
- Read files outside the working directory.
- Read inside `.git/`, `.hg/`, `.svn/` plumbing. Use the user-visible README and code instead.

### Never read — credentials, secrets, tokens (HARD RULE)

The skill MUST skip any file whose path or name matches the patterns below. A matched file is not opened, not partially read, not counted against the budget. If such a file would be referenced by a step, the step records `note: "credentials at <path> — not read by discovery"` and continues. This is a hard rule, not a guideline; matched paths are off-limits regardless of context.

Directories (anywhere in path):
- `auths/`, `auth/` when it contains `*.json` or `*.token`
- `secrets/`, `secret/`
- `credentials/`, `credential/`
- `.aws/`, `.ssh/`, `.gnupg/`, `.netrc`
- `~/.config/<vendor>/auth*` style caches

Files (any depth, case-insensitive on the filename):
- `.env`, `.env.*`, `*.env.local`
- Any filename containing `credential`, `secret`, `password`, `passwd`
- Any filename containing `token` UNLESS the path explicitly contains a non-credential context such as `tokenizer/`, `tokens/test`, `lexer/`, or the file is a `.md` doc; when ambiguous, skip
- Any filename containing `apikey`, `api_key`, `api-key`, `private_key`, `private-key`
- `*.key`, `*.pem`, `*.pfx`, `*.p12`, `*.crt`, `*.cer`
- `id_rsa`, `id_rsa.*`, `id_ed25519`, `id_ed25519.*`, `*_rsa`, `*_ed25519`
- Any file whose first 1 KB matches `BEGIN (RSA|OPENSSH|EC|DSA|ENCRYPTED) PRIVATE KEY` or `aws_secret_access_key` or `client_secret` — treat the partial read as a poison-pill: stop, do not include the path in any output, log the skip

When a directory listing shows a matched path, surface ONE line in the user-visible discovery summary: "skipped credential paths: <count> files under <top-level dir>". Never enumerate matched paths in flows.json, narrations, or notes.

---

## 8. Output writing

The skill writes one HTML file by default. The HTML structure:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>codestory — &lt;repo-name&gt;</title>
    <style id="codestory-theme">/* theme CSS injected here */</style>
  </head>
  <body>
    <!-- renderer DOM: overview SVG, scenes panel, glossary panel -->
    <script id="codestory-data" type="application/json">
      { "units": [...], "flows": [...], "glossary": {...} }
    </script>
    <script id="codestory-runtime">/* renderer JS injected here */</script>
  </body>
</html>
```

The `<script id="codestory-data">` block holds the JSON payload as inert text. The renderer's JS reads it at load time and binds it to the DOM. This is the single permitted injection point; the data is never templated into the HTML body.

### Theme resolution order

The theme is resolved at **activation step 0** (see §1), not at output time. Resolution order (first match wins):

1. `--theme <name>` from the command line — looked up in `renderer/themes/<name>.css`. Recognised names: `cococream`, `dark`, `minimal`, `nothing-design`.
2. `--theme <path>` from the command line — read as a custom CSS file. Triggered when the value contains a path separator or ends in `.css`.
3. Repo manifest — `package.json` `"codestory": { "theme": "<name>" }` or `pyproject.toml` `[tool.codestory] theme = "<name>"`.
4. **Interactive prompt** — the skill asks the user which theme. This is the default path when no flag and no manifest entry exists. The prompt format is documented in §1.
5. `cococream` — silent fallback ONLY when `--no-prompt` is passed or no user channel is available. The fallback is recorded in the discovery summary.

The chosen theme name is recorded in an HTML comment near the top of the document so a reader can reproduce the render.

### `--split` mode

When `--split` is set, the data block is written to a sibling file with the same basename and a `.json` extension. The HTML loads the data via `fetch('codestory.json')` at runtime. Use this mode when the embedded HTML would exceed the 250 KB CI budget.

### `--output <path>`

Default: `./codestory.html` relative to the working directory. The path is created if it does not exist; the file is overwritten if it does — after the re-run merge described in §5 has folded prior hand-edits into the new output.

---

## 8.5 Opt-in screenshot capture

A static-analysis tool cannot guess how to run an arbitrary repo. Screenshots are opt-in via a `codestory.run` manifest block. When that block is absent, the skill does not attempt to start the application, does not launch a browser, and does not enable the `screenshot` viz.

### Manifest schema

`package.json`:

```json
"codestory": {
  "theme": "dark",
  "run": {
    "start": "npm run dev",
    "url": "http://localhost:3000",
    "ready": "GET /",
    "wait_ms": 4000,
    "paths": [
      { "path": "/",        "step": "load-home"     },
      { "path": "/login",   "step": "open-login"    },
      { "path": "/items/1", "step": "view-item"     }
    ]
  }
}
```

`pyproject.toml`:

```toml
[tool.codestory.run]
start   = "uvicorn app.main:app --port 8000"
url     = "http://localhost:8000"
ready   = "GET /healthz"
wait_ms = 4000
paths   = [
  { path = "/",         step = "load-home" },
  { path = "/docs",     step = "open-docs" }
]
```

Fields:

- `start` — string, **required**. Shell command the skill runs to start the app. The user accepts the security and operational risk of running this; the skill does not infer or guess this command.
- `url` — string, **required**. The base URL the headless browser opens.
- `ready` — string, optional. A health check the skill polls before screenshotting; format `"<METHOD> <path>"`. A 2xx response means ready. Default: poll `start` survival + `wait_ms`.
- `wait_ms` — integer, optional. Hard wait before screenshotting. Default 3000.
- `paths[]` — array of `{ path, step }` objects.
  - `path` — URL path relative to `url`. The skill opens `<url><path>`.
  - `step` — the `flow.id` or `flow.id::step.index` to attach the screenshot to. When only `flow.id` is given, the screenshot attaches to the **first** step of that flow.

### Runtime sequence

The capture step runs after Pass 3 (discovery is complete) and before the pre-write validators. The order is:

1. Read `codestory.run` from `package.json` or `pyproject.toml`. If absent: skip the entire capture phase. No browser is launched.
2. Run `start` as a backgrounded subprocess. Capture its PID.
3. Poll the `ready` URL (or sleep `wait_ms`). If the readiness check times out at 30 seconds, the skill kills the subprocess, records a `screenshot_skipped: <reason>` entry in the discovery summary, and continues to write the HTML without screenshots.
4. For each entry in `paths[]`, open `<url><path>` in a headless browser (Playwright is the bundled choice; if unavailable, the skill surfaces a "screenshots requested but Playwright not installed" warning and continues without screenshots).
5. Set viewport `1440 × 900`. Wait for `networkidle`. Capture a PNG.
6. Encode each PNG as a base64 data URI (so the HTML stays self-contained) and attach to the resolved step: `step.screenshot = "data:image/png;base64,..."` and `step.screenshotUrl = "<url><path>"`. The renderer auto-picks `viz: "screenshot"` when `step.screenshot` is set; the skill MAY override with another `viz` if it wants the image used as supporting context only.
7. Send `SIGTERM` to the captured PID. Wait up to 10 seconds; on no exit, `SIGKILL`. Always run this cleanup even on capture failure.
8. Append a `screenshots_captured: <count>` line to the discovery summary printed to the user.

### Size budget

A base64-encoded PNG at `1440 × 900` runs roughly 200–400 KB. The skill keeps the total screenshot payload under **2 MB**; on overrun, it switches to `--split` mode automatically (the data block goes to a sibling `codestory.json`, and screenshots may be written as sibling files under `codestory.assets/<step-id>.png`). The skill records the split decision in the discovery summary.

### Safety

- The skill MUST NOT run `start` unless the user's manifest has a `codestory.run` block — declarative opt-in is the only switch.
- The skill MUST NOT infer a start command from `package.json` scripts or common conventions; an absent block means no run.
- The skill MUST NOT pass arbitrary URLs from outside the manifest to the browser; only `<url><path>` for declared paths.
- The skill skips capture when the working directory has no manifest at all, regardless of `--screenshots`.
- Errors during capture are **non-fatal**. The HTML still renders, just without those images. The skill never aborts the whole `/codestory` run because a screenshot failed.

---

## 9. Failure modes the skill watches at runtime

These are the five scar mitigations framed as runtime guards. Each maps to a check the skill performs and a stop or rewrite action it takes when the check fails.

### R1 — invented flows

**Guard:** every emitted step carries a `file:line` citation in `payload` or `note`, or is `unknown:true` with a `reason`. **Action on failure:** rewrite the step into the unknown shape with a reason that names what was missing. **Place in the flow:** runs after step 5 of the playbook, before the coverage check in step 6. See §3.

### R2 — re-run clobbers hand-edits

**Guard:** prior file is loaded and merged before write; merge key is `(flow.id, step.index)`; prior values that differ from regenerated values win. **Action on failure:** the skill does not write the new file if the merge step fails (e.g. corrupt prior JSON); it surfaces the error and stops. **Place in the flow:** runs immediately before write. See §5.

### R4 — banned phrase slips through

**Guard:** pre-save banned-phrase grep on every narration / payload / note string. **Action on failure:** rewrite the offending string, bounded to three passes per string; on non-convergence, stop and ask the user. **Place in the flow:** runs after step 4 of the playbook, before write. See §4.

### R7 — coverage check silent

**Guard:** unknown count, orphan unit list, and total flow count are printed to the user before write. 30+ flows triggers split-or-filter prompt. **Action on failure:** the skill does not write the HTML until the user has seen the report. **Place in the flow:** runs at step 6 of the playbook. See §6.

### R9 — reading budget blown

**Guard:** per-pass file-read counters compared against 30 / 5 per unit / 3 per flow caps; total counter compared against 200. **Action on failure:** stop further discovery, emit what is collected so far, surface a budget-exhausted notice with a `--scope` narrowing recommendation. **Place in the flow:** runs continuously across passes 1–3 of the playbook. See §7.

### R11 — output schema gaps

**Why this exists:** an early CLIproxyAPI run emitted `{ meta, glossary, flows }` with no `actors`, no `categories`, and step shapes using `{label, title, body, file, lineRef}` instead of `{from, to, transport, payload}`. The HTML still loaded but the diagram was empty and the home page had no chapter cards — the skill produced something that looked like a render but had nothing for the renderer to render. This guard prevents that class of failure.

**Guard — pre-write schema validation.** After the citation guard (R1) and the banned-phrase guard (R4), and before the JSON is serialised to disk, the skill MUST run this validation against the in-memory `data` object:

```python
def validate_output_shape(data):
    errors = []
    # Required top-level keys
    if not isinstance(data.get("project_name"), str) or not data["project_name"].strip():
        errors.append("project_name must be a non-empty string")
    if not isinstance(data.get("actors"), dict) or not data["actors"]:
        errors.append("actors must be a non-empty object keyed by id")
    if not isinstance(data.get("units"), list) or not data["units"]:
        errors.append("units must be a non-empty array (mirror of actors)")
    if not isinstance(data.get("categories"), list) or not data["categories"]:
        errors.append("categories must be a non-empty array")
    if not isinstance(data.get("flows"), list) or not data["flows"]:
        errors.append("flows must be a non-empty array")

    # Categories must cover every flow.category in use
    cat_ids = {c.get("id") for c in data.get("categories", []) if isinstance(c, dict)}
    seen_flow_cats = {f.get("category") for f in data.get("flows", []) if isinstance(f, dict)}
    missing = (seen_flow_cats - cat_ids) - {None}
    if missing:
        errors.append(f"categories missing entries for: {sorted(missing)}")

    # Each flow + step shape
    actor_ids = set(data.get("actors", {}).keys())
    for f in data.get("flows", []):
        for required in ("id", "name", "category", "narration", "steps"):
            if not f.get(required):
                errors.append(f"flow {f.get('id', '?')!r} missing {required!r}")
        for i, s in enumerate(f.get("steps", []) or []):
            for required in ("from", "to", "transport", "payload"):
                if not s.get(required):
                    errors.append(f"flow {f.get('id', '?')!r} step {i} missing {required!r}")
            if s.get("from") and s["from"] not in actor_ids:
                errors.append(f"flow {f.get('id', '?')!r} step {i} from={s['from']!r} not in actors")
            if s.get("to") and s["to"] not in actor_ids:
                errors.append(f"flow {f.get('id', '?')!r} step {i} to={s['to']!r} not in actors")
    return errors
```

**Action on failure.** The skill does NOT write the file with errors present. It attempts ONE regeneration pass, narrow in scope: fill in the missing pieces (build `actors` from referenced ids if it was forgotten; build `categories` from observed `flow.category` values; mirror `name`→`title`; surface step shape gaps as `unknown:true` with a `reason`). It re-runs the validator. If errors remain, it aborts the write and reports the errors verbatim to the user — one line per error, plus a one-line summary of what would need to be filled in to retry.

**Place in the flow.** Runs immediately before serialisation. It is the last gate. After it passes, the skill writes the file and the renderer is guaranteed something to render against.

---

The skill is the union of these nine sections plus the three reference files. The runtime contracts in §3 through §7 are the load-bearing rules; the rest is scaffolding around them. The reference files in `skills/codestory/references/` are read at run time, not paraphrased in this file, so updates to the schema or the voice rules take effect without an edit to SKILL.md.

---

## Runtime sequence

The skill executes one `/codestory` invocation in this strict order. Each phase consumes the prior phase's output; a stop in any phase aborts the run before write.

1. **Parse the invocation.** Read the slash-command form (`/codestory`, `list`, `update`, `theme <name>`, `example [<name>]`) and the four flags (`--scope`, `--theme`, `--output`, `--split`). Resolve the theme per §8 stages 1–4.
2. **Load prior file.** If `codestory.html` (or `codestory.json` with `--split`) exists in the output path, read it and parse the embedded JSON. Keep it in memory as the prior state for §5's merge.
3. **Pass 1 reads.** Scan the working directory at depth 2 (cap 30 files). Identify unit kind and candidate unit ids. If `--scope` is set, only enumerate flows whose chapter matches.
4. **Pass 2 reads.** Per discovered unit (cap 5 files per unit), read entrypoints and collect real source signals: HTTP routes, queue consumers, scheduled jobs, CLI entrypoints, webhook receivers, UI buttons, build/deploy hooks. Record each signal with its `file:line`.
5. **Pass 3 reads.** Per emitted flow (cap 3 files per flow), follow the call sites to confirm the wire shape and key fields of each step. Stop when the 200-read soft total is reached.
6. **Emit steps under the citation rule.** Every step is either cited (`payload` / `note` carries a `file:line` token) or marked `unknown:true` with a `reason`. See §3.
7. **Categorise each flow.** Assign exactly one chapter (`user`, `internal`, `background`, `build`) by primary trigger. See §2 step 5.
8. **Write narrations under the voice contract.** Active voice, subject-verb-object, 60-word soft cap per step, `<span class="who">` and `<span class="what">` markup for unit names and identifiers. See `references/narration-style.md`.
9. **Pre-save banned-phrase grep.** Run the grep over every narration / payload / note. Rewrite any hit; bounded to three passes per string. See §4.
10. **Coverage check.** Print the unknown count, the orphan unit list, and the flow count to the user. On 30+ flows, stop with the split-or-filter prompt. See §6.
11. **Merge with prior state.** Apply the `(flow.id, step.index)` keyed merge from §5. Record stale entries to `.codestory-meta.json`.
12. **Render and write.** Read `renderer/template.html` and the chosen theme CSS. Inject the data block into `<script id="codestory-data">`. Write the HTML to the resolved output path. On `--split`, write the sibling `.json`. Record the chosen theme name in an HTML comment near the top of the document.

Each phase is observable: the skill prints a one-line trace per phase to the chat so the user sees progress and the budget remaining. A phase that stops the run prints the reason and the recommended next invocation (typically a `--scope` narrowing or a `--split` request).

The five runtime guards in §9 are not separate phases — each guard runs inside the phase where its check applies. R1 inside phase 6. R4 inside phase 9. R7 inside phase 10. R2 inside phase 11. R9 continuously across phases 3–5.
