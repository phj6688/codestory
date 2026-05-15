#!/usr/bin/env python3
"""Detect strings whose dominant language differs from the run's chosen pin.

Stdlib only; no model calls. Heuristic combines two signals:

  1. Unicode-block ratio: count chars in language-distinctive blocks
     (Arabic for Farsi/Arabic, Cyrillic for Russian, CJK for Chinese/Japanese,
     Latin-1 supplement / Latin-Extended-A for Western European diacritics).
  2. Stopword grep: word-boundary count of high-frequency function words
     per language.

A string is flagged off-language if EITHER signal scores higher for a
language other than the run's chosen one. A string under 4 words is
considered too short to score and is always treated as on-language —
otherwise short labels like "SQL INSERT" misfire.

CLI:

    python3 ops/lang_guard.py --lang en --data flows.json
    # exit 0 → all strings match `--lang`; prints summary
    # exit 1 → at least one string flagged; prints one line per hit

Returns one line per flagged string, JSON-encoded, to stdout:

    {"path": "flows[0].narration", "detected": "de", "want": "en", "text": "..."}

So the skill can read the report and rewrite the named strings without
re-running detection.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

STOPWORDS = {
    "en": {"the", "and", "of", "to", "with", "for", "when", "that", "is", "in", "on", "a", "an", "are", "as", "be", "by", "this", "it", "from", "or"},
    "de": {"der", "die", "das", "und", "nicht", "mit", "für", "wird", "ist", "ein", "eine", "den", "dem", "auf", "im", "zu", "nach", "von", "auch"},
    "fa": {"که", "این", "آن", "است", "می", "را", "در", "از", "و", "با", "به", "یک", "بر"},
    "fr": {"le", "la", "les", "et", "de", "des", "un", "une", "que", "qui", "dans", "pour", "sur", "avec", "par", "ce", "se"},
    "es": {"el", "la", "los", "las", "y", "de", "del", "un", "una", "que", "para", "con", "por", "es", "se", "no", "como"},
    "ru": {"и", "в", "не", "на", "что", "с", "по", "это", "как", "из", "к", "у", "за", "то"},
}

# Unicode-block votes per language. Each character contributes to at most
# one language; we sum across the string and compare.
def _block_vote(ch: str) -> str | None:
    c = ord(ch)
    if 0x0600 <= c <= 0x06FF or 0xFB50 <= c <= 0xFDFF:  # Arabic
        return "fa"
    if 0x0400 <= c <= 0x04FF:  # Cyrillic
        return "ru"
    if 0x4E00 <= c <= 0x9FFF or 0x3040 <= c <= 0x30FF:  # CJK / Hiragana / Katakana
        return "zh"
    # Latin-Extended-A and Latin-1 supplement diacritics — weak signal for
    # de / fr / es; only counts when stopwords also agree.
    if 0x00C0 <= c <= 0x024F:
        return "diacritic"
    return None


WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿĀ-žА-яا-ي]+", re.UNICODE)
CITATION_RE = re.compile(r"src=\S+")
MARKUP_RE = re.compile(r"<[^>]+>")


def _strip(text: str) -> str:
    text = CITATION_RE.sub(" ", text)
    text = MARKUP_RE.sub(" ", text)
    return text


def detect(text: str) -> str | None:
    """Return the best-guess language code, or None when the string is too short."""
    stripped = _strip(text)
    words = [w.lower() for w in WORD_RE.findall(stripped)]
    if len(words) < 4:
        return None

    # Stopword vote per language.
    stop_score: dict[str, int] = {lang: 0 for lang in STOPWORDS}
    for w in words:
        for lang, sw in STOPWORDS.items():
            if w in sw:
                stop_score[lang] += 1

    # Unicode-block vote.
    block_score: dict[str, int] = {"fa": 0, "ru": 0, "zh": 0, "diacritic": 0}
    for ch in stripped:
        v = _block_vote(ch)
        if v:
            block_score[v] += 1

    # Strong block signals win immediately.
    if block_score["fa"] >= 3:
        return "fa"
    if block_score["ru"] >= 3:
        return "ru"
    if block_score["zh"] >= 3:
        return "zh"

    # Pick the language with the most stopword hits. Tie or zero → English.
    best = max(stop_score, key=stop_score.get)
    if stop_score[best] == 0:
        return "en"  # ASCII-only with no stopwords scores as English by default.

    # Diacritic confirmation: de/fr/es win their stopword vote only if the
    # diacritic block actually fired at least once. Prevents English text
    # ("the order") from being misread.
    if best in ("de", "fr", "es") and block_score["diacritic"] == 0 and stop_score[best] < 2:
        # weak signal — fall back to en if en has any hits, else best.
        if stop_score["en"] > 0:
            return "en"
    return best


def walk(data: dict, want: str) -> list[dict]:
    """Walk the codestory data and flag off-language strings."""
    hits: list[dict] = []

    def check(path: str, text: str) -> None:
        if not isinstance(text, str) or not text.strip():
            return
        detected = detect(text)
        if detected is None or detected == want:
            return
        hits.append({"path": path, "detected": detected, "want": want, "text": text})

    check("lead", data.get("lead", ""))
    for i, f in enumerate(data.get("flows", [])):
        check(f"flows[{i}].narration", f.get("narration", ""))
        check(f"flows[{i}].tagline",   f.get("tagline", ""))
        check(f"flows[{i}].title",     f.get("title", ""))
        for j, s in enumerate(f.get("steps", []) or []):
            check(f"flows[{i}].steps[{j}].payload", s.get("payload", ""))
            check(f"flows[{i}].steps[{j}].note",    s.get("note", ""))
            check(f"flows[{i}].steps[{j}].narration", s.get("narration", ""))
    for term, defn in (data.get("glossary") or {}).items():
        check(f"glossary[{term!r}]", defn)
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(description="codestory language guard")
    ap.add_argument("--lang", required=True, help="ISO 639-1 code the run is pinned to")
    ap.add_argument("--data", required=True, help="path to flows.json")
    args = ap.parse_args()

    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    hits = walk(data, args.lang)
    if not hits:
        print(f"ok: every string scores as {args.lang!s}", file=sys.stderr)
        sys.exit(0)

    for h in hits:
        print(json.dumps(h, ensure_ascii=False))
    print(f"fail: {len(hits)} string(s) off-language", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
