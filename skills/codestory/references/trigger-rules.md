# Trigger rules

When the skill activates and how it reads the invocation surface.

## Activation conditions

The skill activates when ALL of the following are true:

1. The user invokes the `/codestory` slash command in a Claude Code session.
2. The codestory plugin is installed: a `.claude-plugin/plugin.json` file is present in the user plugin directory (`~/.claude/plugins/...`) AND its `name` field reads `codestory`.
3. The session has a working directory the skill can read. The current working directory at invocation time becomes the discovery root.

If the slash command is invoked outside an installed plugin context, the skill returns a one-line installation instruction and stops.

## Invocation surface

The `/codestory` command accepts five invocation forms. They are documented in `commands/codestory.md`; the skill reads the dispatch from the command file.

- `/codestory` — full discovery, write `codestory.html` to the working directory root.
- `/codestory list` — full discovery, print the flow list, do not write the HTML.
- `/codestory update` — full discovery, re-run merge with hand-edit preservation (see SKILL.md §5).
- `/codestory theme <name>` — write the chosen theme name into the repo manifest (`package.json` or `pyproject.toml`) and re-render.
- `/codestory example [<name>]` — render a bundled example from `skills/codestory/examples/`. Defaults to `medchat`.

## Flags

Four flags, all optional. The skill reads them off the command line and applies them in this order: scope → theme → output → split.

- `--scope <category>` — restrict discovery to one of the four chapters: `user`, `internal`, `background`, `build`. The skill emits flows from that chapter only and prints which other chapters it skipped.
- `--theme <name-or-path>` — pass through to the renderer. See theme resolution order below.
- `--output <path>` — write the HTML to the given path instead of `./codestory.html`. Path is relative to the working directory unless absolute.
- `--split` — write the embedded data to a sibling `.json` file next to the HTML. The HTML loads the data via fetch in that mode. The default is to embed inside `<script id="codestory-data" type="application/json">`.

## Theme resolution

Four-stage lookup, first match wins:

1. **Default:** `cococream`. The skill resolves this from `renderer/themes/cococream.css` inside the plugin install dir.
2. **`--theme <name>` from the command line:** the skill looks for `renderer/themes/<name>.css` inside the plugin install dir. Names that resolve: `cococream`, `dark`, `minimal`, `nothing-design`.
3. **`--theme <path>` from the command line:** if the value contains a path separator OR ends in `.css`, the skill reads the file at that path directly and uses it as the theme CSS. The user is responsible for the file's contents.
4. **Repo manifest:** if neither flag is set, the skill reads the project root for a repo-level default:
   - `package.json` → `"codestory": { "theme": "<name>" }`
   - `pyproject.toml` → `[tool.codestory]\ntheme = "<name>"`
   The first one found wins; both present is a warning, not an error.

The chosen theme name is recorded in the output HTML as a comment so a reader can reproduce the render.

## Working directory and reads

The skill's reading budget (SKILL.md §7) applies from the working directory as discovery root.

- Pass 1 scans depth-2 from the root, max 30 files.
- Pass 2 reads up to 5 files per discovered unit.
- Pass 3 reads up to 3 files per flow during call-site verification.
- Soft total across all passes: 200 file reads per `/codestory` run.

The skill never reads files outside the working directory unless the user explicitly points at one via a flag.

## Stop conditions

The skill stops and surfaces a message — never silently — under any of:

- No source signals found (no HTTP routes, no consumers, no entrypoints) after pass 1 and pass 2.
- More than 30 flows discovered: prompts the user with split-or-filter before writing.
- Banned-phrase rewrite loop fails to converge after 3 passes on the same string.
- Reading budget exhausted before pass 3 completes: surfaces what was discovered so far and prompts for a `--scope` narrowing.
