# Large repos — 50+ flows and monorepos

A single rendered HTML book holds about 30 flows comfortably and 50 flows at the byte budget. Past that, the 250 KB CI gate trips and the reader's eye glazes. This document covers the three strategies for getting a useful book out of a large repository.

The skill enforces the first cliff: at 30+ flows discovered, `/codestory` does not write the HTML on the first run. It stops and prompts the user for a split-or-filter decision. That prompt is the entry point to this document.

---

## Strategy 1 — per-scope generation

Each of the four chapters is also a `--scope` value. Run the slash command once per chapter:

```text
/codestory --scope user
/codestory --scope internal
/codestory --scope background
/codestory --scope build
```

Output: four HTMLs, one per chapter. Each one renders only the flows whose `category` matches.

This is the cleanest partition for a typical service-shaped repo. The user chapter answers "what does the customer see?"; the internal chapter answers "what fires when one service calls another?"; the background chapter answers "what runs on a timer?"; the build chapter answers "what happens at deploy?".

Typical naming convention:

```text
out/
├── codestory-user.html
├── codestory-internal.html
├── codestory-background.html
└── codestory-build.html
```

The skill respects the working directory for output. Pass `--output out/codestory-user.html` to drop them in a sibling directory.

---

## Strategy 2 — per-service generation (monorepos)

For monorepos with multiple deployable services, run `/codestory` from each service's own directory. The skill's working directory becomes the discovery root, and the reading budget binds inside that one service.

```bash
cd services/orders && /codestory
cd ../payments    && /codestory
cd ../notify      && /codestory
```

Each service produces its own `codestory.html` next to its `pyproject.toml` (or `package.json`). The result is one book per service, each one capturing the flows that live entirely inside that service plus the outbound calls to its neighbours.

When a flow crosses service boundaries (orders calls payments calls notify), each service captures its own side of the wire. The reader follows the conversation by reading both books.

This is the strategy the medchat repo uses internally: each major surface (`backend`, `frontend`, `iris`) would produce its own book; the medchat example in this repo is the single rendered book for the backend surface.

---

## Strategy 3 — JSON merge (manual; future work)

When a single rendered book is desired and the byte budget allows, multiple `flows.json` files can be merged into one. There is no built-in tool yet; the merge is manual.

The shape:

```bash
# Pseudo-code; not a shipped command.
jq -s '
  {
    units: ([.[].units] | flatten | unique_by(.id)),
    flows: ([.[].flows] | flatten | unique_by(.id)),
    glossary: ([.[].glossary] | add)
  }
' services/orders/flows.json \
  services/payments/flows.json \
  services/notify/flows.json \
  > merged/flows.json
```

Caveats:

- Unit ids must be unique across all sources. If two services have a unit with the same `id`, the merge needs a prefix step first.
- Flow ids must be unique. Prefix with the service name.
- The merged file still has to pass the byte budget after render. 50 flows is approaching the cap.
- Hand-edit preservation does not work across the merge; only the source files retain merge keys.

A shipped `/codestory merge` command is on the roadmap for after v0.1.0. Until then, the manual `jq` merge is the documented path.

---

## When the skill prompts for split-or-filter

The skill's coverage check (discovery step 6) counts flows after enumeration. If the count is 30 or more, the skill stops with:

```text
30+ flows discovered. Split or filter before writing.
Options:
  --scope user|internal|background|build  (renders one chapter only)
  --scope <category> --output <path>      (writes to a non-default path)
  Or split by service: cd into each service directory and run separately.
```

This is the R7 mitigation. The user sees the count and chooses the partition; the skill does not silently emit a 12-flow HTML from a 50-flow repo.

The 30-flow threshold is heuristic — it correlates roughly with the byte budget on average narration length, leaving margin for theme overhead. Repos with sparse narrations may pack 40+ flows under 250 KB; repos with rich narrations may hit the cap at 25 flows. The byte gate in CI is the hard cliff; the 30-flow prompt is the early warning.

---

## Choosing between the three strategies

| Repo shape                                  | Strategy |
|---------------------------------------------|----------|
| One service, 30+ flows, clean chapter split | Per-scope (Strategy 1) |
| Monorepo, 3+ services, each with own README | Per-service (Strategy 2) |
| Migration / archival of a fixed repo        | JSON merge (Strategy 3) |
| Dev iterating on one service in a monorepo  | Per-service in just that directory |

Per-scope is the default when in doubt. The user chapter is almost always the most legible book of a complex repo — it's what the customer cares about, and it's the entry point a new engineer reads first.
