# /codestory

Turn the current repository into a single self-contained animated HTML book of workflows. The real discovery logic lives in `skills/codestory/SKILL.md`; this file is the slash-command surface only.

## Invocations

Five forms.

- `/codestory` — full discovery; write `codestory.html` to the working directory root.
- `/codestory list` — full discovery; print the flow list and the orphan / unknown report; do not write the HTML.
- `/codestory update` — full discovery; merge with the prior `codestory.html` (or `codestory.json` if `--split`) so user hand-edits to narrations, glossary, categories, and steps are preserved. The merge is keyed by `(flow.id, step.index)`; see SKILL.md §5 for the contract.
- `/codestory theme <name>` — write the chosen theme into the repo manifest (`package.json` `"codestory": { "theme": "<name>" }` or `pyproject.toml` `[tool.codestory] theme = "<name>"`), then re-render.
- `/codestory example [<name>]` — render a bundled example. Defaults to `medchat` when no name is given.

## Flags

Four flags, optional, combine freely.

- `--output <path>` — write target. Default is `./codestory.html` relative to the working directory.
- `--split` — write the data block to a sibling `.json` file next to the HTML; the HTML loads it via fetch. Default is to embed inside `<script id="codestory-data" type="application/json">`.
- `--scope <category>` — restrict discovery to one of the four chapters: `user`, `internal`, `background`, `build`. The skill emits flows from that chapter only and reports the chapters it skipped.
- `--theme <name-or-path>` — pick the theme. A bare name resolves against the bundled themes (`cococream`, `dark`, `minimal`, `nothing-design`); a path or any value ending in `.css` is read as a custom theme file.

## Theme resolution

First match wins:

1. `cococream` (default).
2. `--theme <name>` from the command line.
3. `--theme <path>` from the command line (custom CSS file).
4. Repo manifest: `package.json` `"codestory": { "theme": "<name>" }` or `pyproject.toml` `[tool.codestory] theme = "<name>"`.

## Re-run merge

`/codestory update` (and any subsequent `/codestory` run when a prior file is present) preserves user hand-edits. The merge key is `(flow.id, step.index)`. For any paired key, every field where the prior value differs from the regenerated value is preserved. The full contract is in SKILL.md §5 and `skills/codestory/references/schema.md`.

## Examples

```text
/codestory
/codestory list
/codestory --scope internal
/codestory --theme dark
/codestory --theme ./my-theme.css --output docs/architecture.html
/codestory update
/codestory theme nothing-design
/codestory example fastapi-starter
```

Real logic lives in `skills/codestory/SKILL.md`.
