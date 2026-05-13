# Contributing

codestory is MIT-licensed and contributions are welcome. No CLA. MIT means MIT.

This document is the short version of "how to get a change merged". For the design rules see [`docs/SCHEMA.md`](./SCHEMA.md), [`docs/THEMES.md`](./THEMES.md), and [`docs/DISCOVERY.md`](./DISCOVERY.md).

---

## Issues

Four issue templates live at [`.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/). Pick the one that fits:

- [`bug.md`](../.github/ISSUE_TEMPLATE/bug.md) — something is broken; include the reproducer.
- [`feature.md`](../.github/ISSUE_TEMPLATE/feature.md) — propose a new behaviour or invocation.
- [`theme-proposal.md`](../.github/ISSUE_TEMPLATE/theme-proposal.md) — propose a new bundled theme or a structural change.
- [`example-proposal.md`](../.github/ISSUE_TEMPLATE/example-proposal.md) — propose a new bundled example (`examples/<name>`).

A theme proposal that needs a layout change (anything in the structural lock from `docs/THEMES.md`) opens here first. Layout changes are renderer changes, and they merit a design discussion before a PR.

---

## Pull requests

Every PR runs four CI jobs in parallel. **All four must pass before merge.**

- **`lint-skill`** — banned-phrase grep on `skills/codestory/SKILL.md` and its references (excluding `narration-style.md`, which declares the banned list and so legitimately contains every banned phrase as data).
- **`validate-examples`** — schema and coverage rules on every `examples/*/flows.json`. JSON parses, every category is one of the four, every step's `from` / `to` resolves to a unit, no orphan units.
- **`render-examples`** — renders every example × every theme. Asserts each output is under 250 KB. Greps every theme file for layout-modifying CSS (the structural lock).
- **`snapshot-counts`** — diffs the flow / unit / step counts in every example against `.github/snapshots/baseline.json`. Fails on unexpected drift.

A second workflow runs only on PRs:

- **`pr-bytes`** — renders every example × every theme on the PR base and again on the PR head, computes the byte delta per pair, and posts a single sticky comment with a markdown table. Re-runs on every push to the PR. The comment is updated in place rather than appended.

### Branch flow

- Working branches: `feat/<name>`, `fix/<name>`, `chore/<name>`, `refactor/<name>`.
- Merge target: `dev` first, then `master`. Never push directly to `dev` or `master`.

### Commit convention

```
feat(#N): short description
fix(#N): short description
refactor(#N): short description
chore: short description

Closes #N
```

Short imperative subject. No body unless the why genuinely needs prose. No `Co-Authored-By` trailers.

---

## Theme contract

Every theme follows the variable contract in [`docs/THEMES.md`](./THEMES.md). The short version:

- Override every variable at `:root` — all twenty named in the table.
- Do NOT add `grid-template`, `flex-direction`, or `position: absolute|fixed` to structural selectors. CI fails the PR on hit.
- Every `font-family` lists system fallbacks. The `nothing-design` Google Fonts `@import` is the only documented network dependency.

To submit a new bundled theme: open a [`theme-proposal`](../.github/ISSUE_TEMPLATE/theme-proposal.md) issue first. After discussion, the PR adds:

1. `renderer/themes/<your-theme>.css` (copy `_starter.css`, override values).
2. A header comment crediting any external inspiration.
3. A bundled render in each `examples/*` directory as `codestory-<your-theme>.html`.

The CI `render-examples` job builds the rendered files on every push, so the bundled files always reflect the latest theme source.

---

## License and Code of Conduct

The project is MIT-licensed. See [`LICENSE`](../LICENSE).

No CLA. Contributing code under MIT means the contribution is MIT. The maintainer reserves the right to revert anything that breaks the contracts above; the maintainer does NOT reserve any rights over the contributor's code.

We follow the **Contributor Covenant 2.1** code of conduct. The canonical text lives at <https://www.contributor-covenant.org/version/2/1/code_of_conduct/>. Short summary: contribute in a way that makes everyone want to come back. Disagree with ideas, not with people. Report violations to the maintainer email in the repo root `README.md`.
