#!/usr/bin/env python3
"""Create the bilingual, application-facing exercise dataset.

The source fork already contains complete English/Spanish instructions. This
script translates only names through Google's public translation endpoint,
with a persistent cache so interruptions/rate limits are resumable.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

KEEP_INSTRUCTION_LANGS = {"en", "es"}
SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}


def normalize_english(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip())
    words = name.split(" ")
    out: list[str] = []
    for i, word in enumerate(words):
        parts = re.split(r"([/-])", word)
        normalized = "".join(
            p if p in {"/", "-"} or not p else p[0].upper() + p[1:].lower()
            for p in parts
        )
        if i > 0 and normalized.lower() in SMALL_WORDS:
            normalized = normalized.lower()
        out.append(normalized)
    return " ".join(out)


def translate_name(name: str, retries: int = 5) -> str:
    query = urllib.parse.quote(name)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=es&dt=t&q={query}"
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "gym-tracker-dataset/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            result = "".join(part[0] for part in payload[0] if part and part[0]).strip()
            if result:
                return result
            raise ValueError("empty translation")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/exercises.json"))
    parser.add_argument("--output", type=Path, default=Path("data/exercises.es.json"))
    parser.add_argument("--cache", type=Path, default=Path("data/name_translations.en-es.json"))
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    cache = json.loads(args.cache.read_text(encoding="utf-8")) if args.cache.exists() else {}
    result = []
    for index, raw in enumerate(source, 1):
        name_en = normalize_english(raw["name"])
        if name_en not in cache:
            cache[name_en] = translate_name(name_en)
            args.cache.parent.mkdir(parents=True, exist_ok=True)
            args.cache.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            time.sleep(args.delay)
        instructions = raw.get("instructions") or {}
        if not instructions.get("en") or not instructions.get("es"):
            raise ValueError(f"{raw.get('id')}: missing en/es instructions")
        result.append({
            "id": raw["id"],
            "name_en": name_en,
            "name_es": cache[name_en],
            "name": cache[name_en],
            "body_part": raw["body_part"],
            "equipment": raw["equipment"],
            "muscle_group": raw["muscle_group"],
            "secondary_muscles": raw.get("secondary_muscles") or [],
            "target": raw["target"],
            "instructions": {lang: instructions[lang] for lang in KEEP_INSTRUCTION_LANGS},
            "image": raw["image"],
            "gif_url": raw["gif_url"],
        })
        if index % 100 == 0:
            print(f"processed={index}/{len(source)} cache={len(cache)}", flush=True)

    ids = [x["id"] for x in result]
    if len(result) != 1324 or len(set(ids)) != len(ids):
        raise ValueError(f"invalid count/ids: count={len(result)} unique={len(set(ids))}")
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote={args.output} exercises={len(result)} translations={len(cache)}")


if __name__ == "__main__":
    main()
