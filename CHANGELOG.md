# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Per-step visualizer library (`renderer/template.html`): nine viz types beyond the default packet-on-arc — `queue`, `broadcast`, `notification`, `db-write`, `db-read`, `pipeline`, `state`, `screenshot`, plus the existing `hop` / `self`. The skill picks one per step via the §3.1 chooser heuristic in SKILL.md; the renderer dispatches in `renderStep`. Eliminates the "every scene looks the same" failure mode.
- Prev / next step navigation buttons in the player toolbar (`btn-prev`, `btn-next`), wired to the same `step(-1)` / `step(+1)` calls as the arrow keys, with disabled state on the overview view and at the flow boundaries.
- Opt-in screenshot capture: SKILL.md §8.5 defines the contract (`codestory.run` manifest block — `start`, `url`, `paths[]`), and `ops/capture.py` implements the runner (subprocess + Playwright + base64-encoded PNGs into `step.screenshot`). Strictly opt-in; the skill never infers a start command.
- Language pin: SKILL.md §4 mandates one language per render (English default, `--lang <code>` or manifest override), and `ops/lang_guard.py` ships the pre-save detector — Unicode-block ratio + stopword dominance, majority decision per string. The skill shells out to this helper and asks the user to rewrite (or rewrites) any string that scores against the chosen language.
- Schema docs: `references/schema.md` documents the new `viz`, `screenshot`, `screenshotUrl` fields and the chooser heuristic table.

### Changed

- `step(delta)` in the renderer: from overview mode, → / ← now snap to scene 0 / last scene rather than double-advance past the intro. Prev / next buttons and arrow keys behave the same.
- `renderScene` sets `data-viz` on the step label for every scene type (`intro`, `outro`, and each step viz) so a stale badge can never carry over between flows.

### Fixed

- Off-by-one in `step()` when transitioning out of overview mode (the delta was applied twice — once by the overview-snap and once by the bounded clamp). Pressing → from overview now lands on scene 0, not scene 1.

## [0.2.0] - 2026-05-13

### Fixed

- Schema serialisation gap exposed by the first real-world auto-discovery run (CLIproxyAPI): the skill emitted `{ meta, glossary, flows }` with no `actors`, no `categories`, and step shapes using `{ label, title, body, file, lineRef }` instead of `{ from, to, transport, payload }`. The HTML loaded but the diagram was empty and the home page had no chapter cards. SKILL.md §3 now ships a full canonical example JSON and SKILL.md §9 R11 runs a pre-write schema validator that refuses to save a flows.json missing required top-level keys, required flow fields, required step fields, or with step `from`/`to` not referencing an actor id.

### Added

- Renderer normalisation (`renderer/template.html`): the template now reads either `actors` (object) or `units` (array), derives `categories` from `flows[].category` when absent, falls back from `flow.name` → `flow.title`, and from `step.narration` → `step.body`. Defense-in-depth for partial-schema inputs.
- `references/schema.md`: documents the seven canonical top-level keys (`project_name`, `lead`, `actors`, `units`, `categories`, `flows`, `glossary`), the actors / units mirror contract, and the `Category` record shape.
- Per-step required-field validator surfaced as R11 in SKILL.md §9.

### Changed

- The four bundled examples re-rendered against the new template (sizes grew by ~2 KB each from the added normalisation script; all still well under the 250 KB budget — medchat × `nothing-design` is the tightest at 118 KB / 47% of cap).

## [0.1.2] - 2026-05-13

### Changed

- Theme selection moved to activation step 0 — the skill prompts before discovery starts when no `--theme` flag and no repo manifest entry exists. Previous behaviour silently fell back to `cococream`. Resolution order: `--theme` flag → repo manifest → interactive prompt → silent `cococream` (only with new `--no-prompt` flag).

### Added

- `--no-prompt` flag on `/codestory` to suppress the interactive theme picker in scripted / non-interactive contexts.
- README `## Use` section shows the prompt format so first-time users see the theme menu before running.

## [0.1.1] - 2026-05-13

### Added

- Hard exclusion list in `SKILL.md` §7 — discovery never reads credential, secret, token, key, or backup paths (`auths/`, `.env*`, `secrets/`, `.aws/`, `.ssh/`, `*.key`, `*.pem`, `id_rsa*`, `*.bak`, `*.pre-*`, files containing `credential`/`secret`/`password`/`apikey`, and similar). Matched paths are skipped before the budget counter and surfaced as a single summary line — never enumerated in `flows.json`, narrations, or notes.

## [0.1.0] - 2026-05-13

### Added

- Plugin scaffold with `.claude-plugin/plugin.json` manifest.
- Renderer template (`renderer/template.html`) plus four themes: `cococream`, `dark`, `minimal`, `nothing-design`.
- Skill (`skills/codestory/SKILL.md`) and slash command (`/codestory`, `/codestory theme <name>`, `/codestory example`, `/codestory schema`, `/codestory recheck`).
- Four bundled examples — `medchat`, `fastapi-starter`, `nextjs-starter`, `django-celery` — each shipped with `flows.json` and rendered HTML across all four themes.
- Documentation set: `docs/SCHEMA.md`, `docs/THEMES.md`, `docs/DISCOVERY.md`, `docs/LARGE-REPOS.md`, `docs/EXAMPLES.md`, `docs/CONTRIBUTING.md`.
- CI pipeline: `lint-skill`, `validate-examples`, `render-examples`, `snapshot-counts`, plus the PR byte-budget bot enforcing the < 250 KB rendered-HTML budget.
- Release notes draft at `docs/release-notes/v0.1.0.md` covering examples, themes, discovery model, install path, and roadmap.

[Unreleased]: https://github.com/phj6688/codestory/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/phj6688/codestory/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/phj6688/codestory/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/phj6688/codestory/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/phj6688/codestory/releases/tag/v0.1.0
