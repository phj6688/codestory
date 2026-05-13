#!/usr/bin/env python3
"""rendering helper, also used by ci.

Reads renderer/template.html, inlines a theme CSS, and injects a flows.json
into the <script id="codestory-data"> tag. Three modes:

  render mode:
    python3 ops/render.py --theme <name> --data <flows.json> --out <html>

  fixture extract (for tests / examples migration):
    python3 ops/render.py --extract-fixture <medchat-html> --out <json>

  xss self-test:
    python3 ops/render.py --xss-test --out <html>

Theme resolution: --theme accepts a bare name (looked up in renderer/themes/)
or a path ending in .css. Default is 'cococream'.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "renderer" / "template.html"
THEMES_DIR = ROOT / "renderer" / "themes"

DATA_PATTERN = re.compile(
    r'(<script id="codestory-data" type="application/json">)(.*?)(</script>)',
    re.DOTALL,
)
THEME_STYLE_PATTERN = re.compile(
    r'(<style id="codestory-theme">)(.*?)(</style>)',
    re.DOTALL,
)
FLOWS_DATA_SRC_PATTERN = re.compile(
    r'<script id="flows-data" type="application/json">(.*?)</script>',
    re.DOTALL,
)


def resolve_theme(theme_arg: str) -> Path:
    if theme_arg.endswith(".css"):
        p = Path(theme_arg).expanduser().resolve()
        if not p.exists():
            sys.exit(f"theme file not found: {p}")
        return p
    p = THEMES_DIR / f"{theme_arg}.css"
    if not p.exists():
        sys.exit(f"theme not found: {p}")
    return p


def render(theme: str, data_path: Path, out_path: Path) -> None:
    if not TEMPLATE.exists():
        sys.exit(f"template missing: {TEMPLATE}")
    template = TEMPLATE.read_text(encoding="utf-8")

    theme_path = resolve_theme(theme)
    theme_css = theme_path.read_text(encoding="utf-8")

    raw = data_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    # JSON-encode then replace raw '<' and '>' with < / >. JSON.parse
    # decodes the unicode escapes so the JS runtime gets real < and > in the
    # string, which the in-template sanitizer escapes again before injecting
    # into the DOM. Scar R10: guarantees no live <script> substring escapes the
    # data envelope, defeating naive innerHTML injection or grep-visible XSS.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    safe_payload = payload.replace("<", "\\u003c").replace(">", "\\u003e")

    if not DATA_PATTERN.search(template):
        sys.exit("template missing <script id=\"codestory-data\"> tag")
    if not THEME_STYLE_PATTERN.search(template):
        sys.exit("template missing <style id=\"codestory-theme\"> tag")

    merged = THEME_STYLE_PATTERN.sub(
        lambda m: m.group(1) + "\n" + theme_css + "\n" + m.group(3),
        template,
        count=1,
    )
    merged = DATA_PATTERN.sub(
        lambda m: m.group(1) + safe_payload + m.group(3),
        merged,
        count=1,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(merged, encoding="utf-8")
    size = out_path.stat().st_size
    print(f"wrote {out_path} · theme={theme_path.name} · {size} bytes")


def extract_fixture(src_html: Path, out_json: Path) -> None:
    text = src_html.read_text(encoding="utf-8")
    m = FLOWS_DATA_SRC_PATTERN.search(text)
    if not m:
        sys.exit(f"no flows-data script tag found in {src_html}")
    raw = m.group(1).strip()
    data = json.loads(raw)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"extracted fixture: {out_json} · "
          f"actors={len(data.get('actors', {}))} "
          f"categories={len(data.get('categories', []))} "
          f"flows={len(data.get('flows', []))} "
          f"glossary={len(data.get('glossary', {}))}")


def xss_test(out_path: Path) -> None:
    """Render with a payload-laden step note and a malicious narration.

    Confirms the renderer escapes <script> tags rather than passing them
    through innerHTML. Scar R10.
    """
    payload = {
        "project_name": "xss-test",
        "actors": {
            "alice": {"label": "Alice", "tech": "client"},
            "bob": {"label": "Bob", "tech": "server"},
        },
        "categories": [
            {
                "id": "user",
                "title": "XSS test chapter",
                "blurb": "<script>alert('blurb')</script>",
                "mood": "default",
            }
        ],
        "glossary": {},
        "flows": [
            {
                "id": "xss-flow",
                "name": "<script>alert('flowname')</script>",
                "category": "user",
                "color": "#d9462b",
                "trigger": "test",
                "tagline": "<img src=x onerror=alert(1)>",
                "glossary_terms": [],
                "steps": [
                    {
                        "from": "alice",
                        "to": "bob",
                        "transport": "HTTP",
                        "payload": "ok",
                        "note": "<script>alert('note')</script>",
                        "narration": (
                            "<span class=\"who\">alice</span> talks to bob "
                            "<script>alert(1)</script> and also "
                            "<img src=x onerror=alert(1)>"
                        ),
                    }
                ],
            }
        ],
    }
    # write payload to temp and invoke render
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        tmp = Path(f.name)
    render("cococream", tmp, out_path)
    # post-check: rendered HTML must contain the escaped form, not raw <script>alert
    html = out_path.read_text(encoding="utf-8")
    # The JSON-embedded data block legitimately contains the literal text
    # "<script>alert" because that IS the user-supplied narration data. The
    # JS bootstrap escapes it at render time. We confirm the embedded data
    # is inside the JSON envelope (escaped via <\\/) and not as a live script.
    if "<script>alert" in html:
        # any remaining raw "<script>alert" outside the JSON payload would
        # be a real XSS. The render() escaper turns </ into <\/ inside the
        # data block so the only legal occurrence is in the visible test
        # text after JS escapeHtml runs at runtime. For static analysis
        # purposes (grep gate), there must be NO occurrence of the literal
        # "<script>alert" in the static HTML output.
        sys.exit(
            "FAIL: raw '<script>alert' appears in rendered HTML — "
            "scar R10 escape regression"
        )
    print(f"xss-test PASSED · {out_path} ({out_path.stat().st_size} bytes)")


def main() -> None:
    ap = argparse.ArgumentParser(description="codestory renderer helper")
    ap.add_argument("--theme", default="cococream")
    ap.add_argument("--data")
    ap.add_argument("--out")
    ap.add_argument("--extract-fixture", dest="extract_fixture")
    ap.add_argument("--xss-test", action="store_true")
    args = ap.parse_args()

    if args.extract_fixture:
        if not args.out:
            ap.error("--out required with --extract-fixture")
        extract_fixture(
            Path(args.extract_fixture).expanduser().resolve(),
            Path(args.out).expanduser().resolve(),
        )
        return

    if args.xss_test:
        if not args.out:
            ap.error("--out required with --xss-test")
        xss_test(Path(args.out).expanduser().resolve())
        return

    if not args.data or not args.out:
        ap.error("--data and --out are required (or use --extract-fixture / --xss-test)")
    render(
        args.theme,
        Path(args.data).expanduser().resolve(),
        Path(args.out).expanduser().resolve(),
    )


if __name__ == "__main__":
    main()
