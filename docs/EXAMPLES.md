# Bundled examples

codestory ships four worked examples under `examples/`. Each example is a complete `flows.json` plus four pre-rendered HTMLs (one per bundled theme). The examples are reference material for what good output looks like and they are CI ground truth for the validate / render / snapshot jobs.

When the user invokes `/codestory example <name>`, the skill resolves `<name>` to one of the directories below and opens the rendered HTML for the active theme. The default theme is `cococream`; pass `--theme <name>` to pick another, or `/codestory theme <name>` to change the repo default.

---

## `examples/medchat`

A real medical chat application. 17 units, 18 flows, 81 steps. The largest book bundled and the one that proves the format scales past the 30-flow split prompt without breaching the 250 KB byte budget.

The book covers user-triggered flows (sign-up, post a message, direct chat, group chat), internal flows (the RAG pipeline, the message broker fan-out, the embedding writer), background flows (the nightly re-index, the orphan cleanup) and build flows (database migrations, container build).

medchat is the gold standard: every step cites a real `src=<path>:<line>`, every narration passes the voice contract, and every chapter is populated.

- [`examples/medchat/README.md`](../examples/medchat/README.md)
- [`examples/medchat/flows.json`](../examples/medchat/flows.json)

---

## `examples/fastapi-starter`

A small synthetic FastAPI project with three flows: a user POST that inserts an order, a `BackgroundTasks` receipt task that fires after the response, and an Alembic migration that runs on the startup event.

The smallest plausible service-shaped book. Useful when a contributor wants to see the minimum viable shape of a `flows.json` — the schema fully populated, the citations all real, the four-chapter division working with just three flows.

Four units: Client, FastAPI app, Postgres, SMTP relay. Three categories: `user`, `internal`, `build` (no `background` because nothing is scheduled).

- [`examples/fastapi-starter/README.md`](../examples/fastapi-starter/README.md)
- [`examples/fastapi-starter/flows.json`](../examples/fastapi-starter/flows.json)

---

## `examples/nextjs-starter`

A synthetic Next.js App Router project with three flows including a Stripe webhook. The webhook flow is the example that demonstrates the inbound-webhook signal in the discovery playbook — the route receives a request the application did not originate, and the narration spells out the verification step.

Four units: Visitor, Next.js app, Stripe, Postgres. Categories: `user`, `internal`, `build`.

This is the example to read when a contributor is adding Next.js or any other Node.js stack support. The unit shapes and the route shapes carry over almost directly.

- [`examples/nextjs-starter/README.md`](../examples/nextjs-starter/README.md)
- [`examples/nextjs-starter/flows.json`](../examples/nextjs-starter/flows.json)

---

## `examples/django-celery`

A synthetic Django + Celery project with five flows. Includes a Celery beat schedule (the only example that exercises the `background` chapter at full depth) and a worker consumer that fans out from a queue.

Seven units: User, Django app, Postgres, RabbitMQ broker, Celery worker, Celery beat, S3. Five flows across all four chapters. The largest of the three synthetic starters and the one that demonstrates the full set of transports: HTTP, SQL, AMQP publish, AMQP consume, S3 PUT.

Use this example when working on a Python repo with workers and schedulers.

- [`examples/django-celery/README.md`](../examples/django-celery/README.md)
- [`examples/django-celery/flows.json`](../examples/django-celery/flows.json)

---

## `/codestory example <name>` behaviour

The invocation form: `/codestory example [<name>] [--theme <name>]`.

The skill resolves `<name>` to a path under `examples/`. The default name is `medchat`.

Resolution order:

1. Skill resolves `<name>` to `examples/<name>/`.
2. Reads the active theme from the flag (`--theme <name>`) or the repo manifest, falling back to `cococream`.
3. Resolves to `examples/<name>/codestory-<theme>.html` — one of the four pre-rendered HTMLs that ship with the example.
4. Returns the file path to the caller.

Each example directory ships all four pre-rendered HTMLs so the slash command never has to re-render at example time — the skill just resolves and returns the path. CI regenerates these HTMLs on every push (the `render-examples` job), so the bundled files stay in sync with the source `flows.json` and the current theme CSS.

Example invocations:

```text
/codestory example                           # → examples/medchat/codestory-cococream.html
/codestory example fastapi-starter           # → examples/fastapi-starter/codestory-cococream.html
/codestory example nextjs-starter --theme dark
/codestory example django-celery --theme nothing-design
```

The flag order is the same as the standard `/codestory` invocation: `--scope`, `--theme`, `--output`, `--split`.
