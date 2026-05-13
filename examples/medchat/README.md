# medchat — gold-standard example

`medchat` is a self-hosted medical chat assistant: a chat front-end, a local resident model, a cloud orchestrator routed through Claude Sonnet, a citation-checking gate, a pgvector RAG corpus, an audit trail, and a small set of cron jobs. This bundle ships the migrated `flows.json` and four pre-rendered HTMLs (one per theme). It is the largest fixture and the byte-budget reference.

The source `flows.json` was migrated from `~/projects/medchat/20260512_medchat_flows.html`. Counts: **18 flows**, **17 units**, 57 glossary terms.

## Units (17)

| id | role |
|---|---|
| user | End user typing questions in a browser session. |
| cf | Cloudflare Tunnel terminating TLS and piping traffic into the homelab. |
| traefik | Reverse proxy that routes Host headers to the right internal container. |
| openwebui | Chat front-end; speaks the OpenAI API to local and remote model backends. |
| operator | Host shell account running scripts and docker compose commands. |
| cron | Host scheduler that fires the three nightly and per-minute jobs. |
| medchat_mcp | FastAPI sidecar exposing tools, citecheck, the MCP server, and the audit endpoints. |
| ingest | Batch worker that fetches corpora, embeds chunks, and upserts pgvector rows. |
| llama | Resident llama-server process running MedGemma-4B with the OpenAI API on :8080. |
| nexus | Remote nexus-router proxy to Claude Sonnet for the cloud route. |
| ollama | Local embedding server running qwen3-embedding:8b. |
| files | Files microservice serving uploaded document retrieval. |
| postgres | PostgreSQL with pgvector storing audit rows, RAG chunks, and embeddings. |
| ext_med_apis | PubMed, ClinicalTrials, OpenFDA, RxNorm, EuropePMC public APIs. |
| ext_corpora | DailyMed, CDC, NIH, USPSTF, WHO and other source corpora fetched nightly. |
| huggingface | Model registry the resident model weights are downloaded from once. |
| host_fs | Host disk path for logs, sentinels, and the BENCHMARKS.md audit trail. |

## Flows (18)

### user — when a user asks a question

| id | title | one-liner |
|---|---|---|
| f1-direct-chat | Direct chat | Cloudflare → Traefik → OpenWebUI → resident llama-server. |
| f2-tools-chat | Tools chat | The local model emits a tool call; OpenWebUI dispatches to medchat-mcp. |
| f3-cloud-consult-rest | Cloud consult (REST) | The orchestrator drives Claude Sonnet through a bounded tool loop, then citecheck. |
| f4-mcp-consult | MCP consult | An external MCP client opens an SSE channel to `/mcp`; same loop, different doorway. |
| f5-rag-search | RAG search | Ollama embed → pgvector cosine lookup → top-k chunks tagged `[RAG:<chunk_id>]`. |
| f6-attached-file | Attached file | medchat-mcp asks files-service for the snippets matching the uploaded document. |

### internal — behind the scenes

| id | title | one-liner |
|---|---|---|
| f7-citecheck | citecheck gate | quiesce check, evidence-pack rebuild, marker resolution, observation update. |
| f8-verify | Local verify | MedGemma reads the cleaned draft and votes per sentence; never calls tools. |
| f9-quiesce-reopen | Admin reopen | Operator POSTs to `/admin/quiesce/reopen` with the admin bearer token. |
| f10-audit-turn | Audit turn | Every turn writes content_text + content_hash to medchat.turn in one statement. |

### background — scheduled jobs

| id | title | one-liner |
|---|---|---|
| f11-cron-ingest | Nightly ingest | Walk each corpus, skip unchanged chunks by content hash, embed and upsert the rest. |
| f12-cron-scrub | Audit scrub | Rows older than MEDCHAT_AUDIT_RETENTION_DAYS get content_text=NULL; hash survives. |
| f13-cron-vram | VRAM watch | Every minute, verify-ceiling.sh appends a JSON line and toggles the alarm sentinel. |

### build — deploy and setup

| id | title | one-liner |
|---|---|---|
| f14-deploy | Deploy | docker compose up --build --force-recreate; healthcheck gates OpenWebUI; alembic upgrade. |
| f15-setup-openwebui | OWUI setup | Sign in, discover models, write the system prompt and the tool server connection. |
| f16-download-model | Model download | Pull the Q4_K_M .gguf from HuggingFace into the shared ./models directory. |
| f17-bench | Bench gate | Run every TASKSPEC bench gate in order; > 15% regression halts the ship. |
| f18-tool-harness | Tool harness | Replay 50 happy-path and 15+ adversarial prompts; grade tool selection. |

## Re-run merge contract (R2 demonstration)

Hand-edits to any narration, payload, note, or unit role in this file survive a later `/codestory update` run. The skill keys merges by:

- `(flow.id, step.index)` for step fields (`from`, `to`, `transport`, `payload`, `note`, `narration`)
- `flow.id` for flow-level fields (`title`, `narration`, `category`)
- `unit.id` for unit-level fields (`label`, `role`, `kind`)
- the term string for glossary entries

For every paired key present in both the prior file and the regenerated data, the merge compares each field. If the prior value differs from the regenerated value, the prior value is treated as a hand-edit and preserved. New entries from the regenerated run with no prior key are appended. Prior entries with no regenerated counterpart are kept and marked `stale:true` in a sibling `.codestory-meta.json`, never silently dropped.

A reviewer who edits, say, the f3-cloud-consult-rest step 1 narration ("model='claude-sonnet-4-6'") to add nuance — "model='claude-sonnet-4-6', tool_choice='auto', max_rounds=3 by config" — will see that edit preserved across the next `/codestory update`. The skill prints a one-line summary naming preserved keys so the user can audit the diff.

## Rendered output

Pre-rendered per theme:

- `codestory-cococream.html`
- `codestory-dark.html`
- `codestory-minimal.html`
- `codestory-nothing-design.html`

Each render is well under the 250 KB budget (largest sits near 116 KB with the `nothing-design` theme).
