# Narration style

This file declares the voice contract for every word the skill emits into `flows.json`. The skill consults this file before saving and rewrites any narration that violates a rule below.

Note: this file IS the declaration of the banned-phrase list. The phrases appear here as data. They are forbidden everywhere else in the shipped skill text and in every emitted narration.

## Voice rules

1. **Active voice, subject-verb-object.** Each sentence names a doer, a verb, and a target. "The API writes the row." Not "A row is written." The reader needs to see who acts on what.
2. **Complete sentences only.** No fragments, no headlines, no list-as-sentence shorthand. Each sentence stands on its own and parses without context.
3. **Define jargon on first use within a flow's narration.** If a flow's narration introduces "idempotency key", the same flow's narration must define what it is in plain English before relying on the term. Subsequent flows may assume the term.
4. **Connect cause and effect across sentences.** If sentence two depends on sentence one, the link must be explicit ("because", "so", "after that", "in response"). The reader should never need to infer.
5. **Soft cap: 60 words per step.** A step's narration that runs longer signals that the step is doing too much; split it.

## Markup contract

Two inline spans, both rendered with paired CSS by every theme.

- `<span class="who">…</span>` wraps service, package, app, or module names. One occurrence per name per sentence. Example: `<span class="who">orders-api</span> writes the row.`
- `<span class="what">…</span>` wraps identifiers: route paths, function names, env var names, database tables, queue topic names. Example: `<span class="who">orders-api</span> calls <span class="what">POST /v1/payments</span> on the payments service.`

No other raw HTML is permitted in narration text. The renderer escapes everything else.

## Banned-phrase list

The skill greps every narration string against this list before saving the JSON. On hit, the skill rewrites the offending narration and re-checks until clean. The list is verbatim from TASKSPEC §9.

- handles
- manages
- deals with
- communicates with
- leverages
- robust
- gracefully
- for clarity
- this ensures
- straightforward

Why each is banned:

- "handles" and "manages" hide the actual verb. Replace with the specific verb: writes, reads, retries, schedules, validates, signs, etc.
- "deals with" is even vaguer. Same fix.
- "communicates with" hides the transport. Replace with the wire shape: "calls", "publishes to", "subscribes from", "writes to the table".
- "leverages" is filler. Replace with the verb that names the action.
- "robust" is a claim with no content. Either describe the specific failure modes the code covers, or drop the word.
- "gracefully" is the same kind of empty adverb. Name the exact behaviour: "returns 503", "retries with backoff", "logs and continues".
- "for clarity" announces that the next sentence needed a preamble. Cut it; rewrite the next sentence so it stands alone.
- "this ensures" claims a guarantee without naming the mechanism. Replace with a sentence that names the mechanism: "The unique index on `id` rejects duplicate inserts."
- "straightforward" is self-congratulation. Either the reader sees the step is simple, or they do not — the word adds nothing.

## Pre-save check

The skill executes this check before writing `flows.json`:

1. Collect every `narration` string from every flow, plus every `payload` and `note` string from every step.
2. Grep each collected string against the banned-phrase list above, case-insensitive, word-boundary aware.
3. On any hit, rewrite the offending string by replacing the banned phrase with a concrete verb, identifier, or specific behaviour that names the mechanism.
4. Re-run steps 1–3 until no hits remain.
5. Only then write the JSON to disk.

A hit MUST NOT be passed through with a note. The rewrite is mandatory.

## Examples

Bad:
> The orders service handles incoming requests robustly and communicates with the payments service to ensure the transaction completes.

Good:
> `<span class="who">orders-api</span>` accepts `<span class="what">POST /v1/orders</span>` and validates the body against the `Order` schema. On success, the service calls `<span class="what">POST /v1/payments</span>` on `<span class="who">payments-api</span>` with an idempotency key derived from the order id; the payments service rejects duplicate idempotency keys with a 409, which the orders service catches and treats as a no-op.

Bad:
> The worker gracefully manages job retries.

Good:
> `<span class="who">orders-worker</span>` re-enqueues the job onto `<span class="what">orders.retry</span>` with a 30-second visibility timeout when the inner step raises `<span class="what">TransientError</span>`. After three retries the worker writes the job id to `<span class="what">orders.dead_letter</span>` and stops.

Bad:
> For clarity, this ensures idempotency.

Good:
> The `Idempotency-Key` header threads through every retry. The unique index on `payments.idempotency_key` rejects a duplicate write with a constraint violation, which the API catches and returns as `200 OK` carrying the original response body.
