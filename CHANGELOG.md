# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

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
