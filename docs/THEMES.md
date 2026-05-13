# Themes

codestory ships four themes and one starter template. A theme is a CSS file under `renderer/themes/` that overrides the variables declared in `renderer/themes/_starter.css`. Layout is locked; only the variable values and a small set of animation rules are negotiable.

This document is the contract every theme follows. CI enforces it on every PR.

---

## Bundled themes

| Theme            | File                                  | Notes |
|------------------|---------------------------------------|-------|
| `cococream`      | `renderer/themes/cococream.css`       | Default. Warm paper background, serif headlines, red accent. |
| `dark`           | `renderer/themes/dark.css`            | Near-black background, warm grey ink, amber-coral accent. |
| `minimal`        | `renderer/themes/minimal.css`         | White and black, no colour. Animations fade-only. Designed for print and PDF. |
| `nothing-design` | `renderer/themes/nothing-design.css`  | Strict Nothing OS rule set. Imports Space Grotesk + Space Mono with system fallbacks. |

Theme resolution order (first match wins):

1. `cococream` — the default.
2. `--theme <name>` — looked up at `renderer/themes/<name>.css`.
3. `--theme <path>` — read directly if the value contains a path separator or ends in `.css`.
4. Repo manifest — `package.json` `"codestory": { "theme": "<name>" }` or `pyproject.toml` `[tool.codestory] theme = "<name>"`.

---

## Variable contract

Every theme must declare the full variable set at `:root`. The renderer reads these — a theme that omits one breaks the layout for that token. Verbatim from TASKSPEC §5:

| Variable          | Role |
|-------------------|------|
| `--bg`            | Page background. The dominant surface colour. |
| `--bg-2`          | Secondary surface — sidebar / panel-on-page tone. |
| `--panel`         | Card / panel face — what story cards sit on. |
| `--panel-2`       | Deeper panel — speech bubble fill, pressed-state background. |
| `--line`          | Hairline dividers, card borders. |
| `--ink`           | Primary text colour. |
| `--mute`          | Secondary text — taglines, labels. |
| `--dim`           | Tertiary text — meta lines, timestamps. |
| `--accent`        | Primary accent — chapter numerals, active states. |
| `--accent-2`      | Deeper accent — pressed key, hover-locked borders. |
| `--accent-soft`   | Tinted accent — pill background, soft chrome (`rgba` allowed). |
| `--warn`          | Unknown-step / warning state colour. |
| `--packet`        | SVG animated packet fill. |
| `--paper-dot`     | Page dot-pattern tone (transparent allowed). |
| `--font-serif`    | Display and body serif. System fallbacks required. |
| `--font-sans`     | UI sans — buttons, hints. System fallbacks required. |
| `--font-mono`     | Tech labels, transports, payloads. System fallbacks required. |
| `--card-radius`   | Corner radius for cards, pills, panels. |
| `--shadow-offset` | Drop-shadow offset for floating panels (`0` disables). |
| `--bg-pattern`    | Repeatable background pattern (`none` disables). |

A theme may not reduce the variable set — every `:root` block in `renderer/themes/*.css` declares all 20.

---

## How to write a custom theme

Three steps.

**1. Copy the starter.**

```bash
cp renderer/themes/_starter.css renderer/themes/midnight.css
```

The starter declares every variable with a one-line role comment. Edit values, save.

**2. Override the values.**

Open the file and change colours, fonts, radii, shadow. Keep every variable name; only the right-hand side is yours.

**3. Render with your theme.**

```bash
python3 ops/render.py \
  --theme renderer/themes/midnight.css \
  --data examples/fastapi-starter/flows.json \
  --out out/midnight.html
```

Or, from a `/codestory` invocation:

```text
/codestory theme renderer/themes/midnight.css
```

The renderer accepts the bare name (looked up in `renderer/themes/`) or a path ending in `.css`.

---

## Structural lock

Themes override variables. Themes do NOT modify layout.

CI greps every theme file under `renderer/themes/` for layout-modifying CSS. The rule fails on any match outside a comment:

- `grid-template` (and its longhand variants).
- `flex-direction` on structural selectors.
- `position: absolute` or `position: fixed` on structural selectors.

A theme that needs different positioning is a renderer change, not a theme change. Open an issue with the `theme-proposal` template before submitting a PR.

What themes MAY change:

- Every value of every variable in the table above.
- Animation timing and easing on existing transitions.
- Font choices (with system fallbacks on every declaration).
- Background pattern (`--bg-pattern`).
- Shadow depth (`--shadow-offset`).

What themes MAY NOT change:

- The overview ↔ scenes split layout.
- The four-chapter structure of the document.
- SVG geometry of the flow paths.
- Keyboard bindings.
- The header, the side panel, or the footer layout boxes.

The contract is enforced on every CI run. See `.github/workflows/ci.yml` job `render-examples` for the exact grep.

---

## `nothing-design` lineage

The `nothing-design` theme is a strict transcription of the Nothing design language to web. The source spec is the `nothing-design` Claude skill at the path `~/.claude/skills/nothing-design/SKILL.md` (a global skill installed under the user's `~/.claude/skills` directory; reference is by path, not a relative link, since the source lives outside this repository).

What the theme transcribes from that source:

- The monochrome palette, dot-grid background, and shadow-free chrome.
- Space Grotesk for display and body, Space Mono for technical labels (transports, payloads).
- Strict hierarchy: large display sizes, generous whitespace, no decorative gradients.

What the theme allows itself that no other theme does:

- One documented external dependency: `@import` for Space Grotesk and Space Mono from Google Fonts.

To keep offline rendering intact, every `font-family` declaration in `nothing-design.css` lists system fallbacks:

- Space Grotesk → Inter → `-apple-system` → `BlinkMacSystemFont` → `system-ui` → `sans-serif`.
- Space Mono → JetBrains Mono → `ui-monospace` → `Menlo` → `Consolas` → `monospace`.

When the network blocks Google Fonts, the system fallback substitutes and every Nothing rule stays intact: hierarchy, spacing, monochrome, no shadows. The offline render is tested as a CI variant.

Credit: the theme would not exist without the `nothing-design` skill specification. The header comment in `renderer/themes/nothing-design.css` carries the same credit inline.
