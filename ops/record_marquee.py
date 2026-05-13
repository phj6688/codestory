#!/usr/bin/env python3
# Headless chromium recording of an animated codestory flow. Output is a webm
# the ffmpeg step turns into the README marquee GIF.

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def record(
    html: Path,
    chapter_title: str,
    story_title: str,
    out_dir: Path,
    width: int,
    height: int,
    home_dwell_ms: int,
    chapter_dwell_ms: int,
    overview_dwell_ms: int,
    max_play_seconds: float,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(out_dir),
            record_video_size={"width": width, "height": height},
        )
        page = context.new_page()

        url = f"file://{html.resolve()}"
        page.goto(url, wait_until="domcontentloaded")

        page.wait_for_selector("#v-home.active", timeout=10000)
        page.wait_for_selector(".cats .cat", timeout=5000)
        page.wait_for_timeout(home_dwell_ms)

        cat = page.locator(".cats .cat", has_text=chapter_title).first
        cat.click()
        page.wait_for_selector("#v-chapter.active", timeout=5000)
        page.wait_for_selector(".story-card", timeout=5000)
        page.wait_for_timeout(chapter_dwell_ms)

        story = page.locator(".story-card", has_text=story_title).first
        story.click()
        page.wait_for_selector("#v-player.active", timeout=5000)
        page.wait_for_selector("#btn-pause", timeout=5000)
        page.wait_for_timeout(overview_dwell_ms)

        close = page.locator("#shortcuts-close")
        if close.count() and close.is_visible():
            close.click()
            page.wait_for_timeout(250)

        page.locator("#btn-pause").click()

        deadline = time.time() + max_play_seconds
        while time.time() < deadline:
            label = page.locator("#btn-pause").inner_text()
            count_text = page.locator("#scene-count").inner_text()
            try:
                cur, total = [int(x.strip()) for x in count_text.split("/")]
            except Exception:
                cur, total = 0, 0
            if label.strip().lower() == "play" and cur >= total and total > 0:
                break
            page.wait_for_timeout(250)

        page.wait_for_timeout(600)
        video_path = page.video.path() if page.video else None
        context.close()
        browser.close()

    if not video_path:
        raise RuntimeError("playwright did not produce a video path")

    final = out_dir / "marquee-source.webm"
    shutil.move(video_path, final)
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--chapter", default="When a user asks a question")
    parser.add_argument("--story", default="Direct chat")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--home-dwell-ms", type=int, default=1400)
    parser.add_argument("--chapter-dwell-ms", type=int, default=1100)
    parser.add_argument("--overview-dwell-ms", type=int, default=900)
    parser.add_argument("--max-play-seconds", type=float, default=22.0)
    args = parser.parse_args()

    video = record(
        args.input,
        args.chapter,
        args.story,
        args.out_dir,
        args.width,
        args.height,
        args.home_dwell_ms,
        args.chapter_dwell_ms,
        args.overview_dwell_ms,
        args.max_play_seconds,
    )
    print(str(video))
    return 0


if __name__ == "__main__":
    sys.exit(main())
