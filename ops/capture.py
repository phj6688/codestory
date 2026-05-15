#!/usr/bin/env python3
"""Screenshot capture for the opt-in `codestory.run` flow.

Reads the working directory's manifest (`package.json` "codestory.run" or
`pyproject.toml` [tool.codestory.run]), starts the target app as a
backgrounded subprocess, waits for readiness, drives Playwright to
capture every declared path at 1440×900, base64-encodes each PNG into the
matching `step.screenshot` field of the supplied flows.json, and tears the
subprocess down on the way out. Mutates `flows.json` in place.

Strictly opt-in: when no `codestory.run` block is present, the script
exits 0 with a one-line skip notice on stderr.

Playwright is an optional dependency. When the import fails the script
exits 0 with an instructional notice; the rest of the /codestory run
continues without screenshots. This matches the SKILL.md §8.5 contract
(capture failure is non-fatal).

CLI:

    python3 ops/capture.py --data flows.json --root .
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _load_manifest(root: Path) -> dict | None:
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            run = (data.get("codestory") or {}).get("run")
            if isinstance(run, dict):
                return run
        except json.JSONDecodeError:
            pass

    pyp = root / "pyproject.toml"
    if pyp.exists():
        try:
            import tomllib  # 3.11+
        except ImportError:
            return None
        try:
            data = tomllib.loads(pyp.read_text(encoding="utf-8"))
            run = (data.get("tool") or {}).get("codestory", {}).get("run")
            if isinstance(run, dict):
                return run
        except Exception:
            pass
    return None


def _wait_ready(base_url: str, ready: str | None, wait_ms: int) -> bool:
    """Poll the readiness probe (if any) up to 30s, then sleep wait_ms."""
    if ready:
        method, _, path = ready.partition(" ")
        url = base_url.rstrip("/") + (path or "/").strip()
        deadline = time.monotonic() + 30.0
        req = urllib.request.Request(url, method=method.upper() or "GET")
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(req, timeout=2) as r:
                    if 200 <= r.status < 300:
                        time.sleep(wait_ms / 1000.0)
                        return True
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                pass
            time.sleep(0.5)
        return False
    time.sleep(wait_ms / 1000.0)
    return True


def _resolve_step(flows: list[dict], target: str) -> tuple[int, int] | None:
    """Parse `flow.id` or `flow.id::step.index`; return (flow_idx, step_idx)."""
    flow_id, _, step_idx = target.partition("::")
    for fi, f in enumerate(flows):
        if f.get("id") == flow_id:
            si = int(step_idx) if step_idx.isdigit() else 0
            if 0 <= si < len(f.get("steps") or []):
                return fi, si
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="codestory screenshot capture")
    ap.add_argument("--data", required=True, help="path to flows.json to mutate")
    ap.add_argument("--root", default=".", help="manifest root (default: cwd)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    run_cfg = _load_manifest(root)
    if not run_cfg:
        print("capture: no codestory.run manifest block; skipping screenshots", file=sys.stderr)
        return

    start = run_cfg.get("start")
    base_url = run_cfg.get("url")
    paths = run_cfg.get("paths") or []
    if not start or not base_url or not paths:
        print("capture: codestory.run missing start/url/paths; skipping", file=sys.stderr)
        return

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        print(
            "capture: playwright not installed — `pip install playwright && playwright install chromium`",
            file=sys.stderr,
        )
        return

    data_path = Path(args.data).resolve()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    flows = data.get("flows") or []

    # start the app
    print(f"capture: starting `{start}`", file=sys.stderr)
    proc = subprocess.Popen(
        start,
        shell=True,
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
    )

    captured = 0
    try:
        ok = _wait_ready(base_url, run_cfg.get("ready"), int(run_cfg.get("wait_ms", 3000)))
        if not ok:
            print("capture: readiness probe timed out; skipping", file=sys.stderr)
            return

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            for entry in paths:
                p = entry.get("path", "/")
                target = entry.get("step")
                if not target:
                    continue
                full = base_url.rstrip("/") + p
                try:
                    page.goto(full, wait_until="networkidle", timeout=15000)
                    png = page.screenshot(type="png")
                except Exception as e:
                    print(f"capture: {full} failed: {e}", file=sys.stderr)
                    continue
                resolved = _resolve_step(flows, target)
                if not resolved:
                    print(f"capture: target {target!r} did not resolve to a step", file=sys.stderr)
                    continue
                fi, si = resolved
                step = flows[fi]["steps"][si]
                step["screenshot"] = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
                step["screenshotUrl"] = full
                captured += 1
            browser.close()
    finally:
        try:
            if hasattr(os, "killpg"):
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
        except ProcessLookupError:
            pass

    if captured:
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"capture: wrote {captured} screenshot(s) into {data_path.name}", file=sys.stderr)
    else:
        print("capture: no screenshots captured", file=sys.stderr)


if __name__ == "__main__":
    main()
