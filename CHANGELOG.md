# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

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

[Unreleased]: https://github.com/phj6688/codestory/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/phj6688/codestory/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/phj6688/codestory/releases/tag/v0.1.0
