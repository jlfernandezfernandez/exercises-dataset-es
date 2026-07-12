#!/usr/bin/env python3
"""Build the versioned dataset release assets."""

import argparse
import gzip
import hashlib
import json
import tarfile
from pathlib import Path

ARCHIVE_NAME = "exercise-dataset.tar.gz"
ALLOWED_FILES = ("data/exercises.json", "LICENSE", "NOTICE.md")


def load_entries(root: Path) -> list[dict]:
    entries = json.loads((root / "data/exercises.json").read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries:
        raise ValueError("data/exercises.json must be a non-empty array")
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("id"):
            raise ValueError("every exercise must have an id")
        for field in ("image", "gif_url"):
            path = entry.get(field)
            if not isinstance(path, str) or not path:
                raise ValueError(f"exercise {entry['id']} has no {field}")
            if not (root / path).is_file():
                raise FileNotFoundError(path)
    return entries


def normalized_info(path: Path, name: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = path.stat().st_size
    info.mode = 0o644
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def build_release(root: Path, output: Path, version: str) -> dict:
    entries = load_entries(root)
    media = sorted({entry[field] for entry in entries for field in ("image", "gif_url")})
    names = [*ALLOWED_FILES, *media]
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / ARCHIVE_NAME

    with archive_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for name in names:
                    path = root / name
                    with path.open("rb") as source:
                        archive.addfile(normalized_info(path, name), source)

    manifest = {
        "schema_version": 1,
        "dataset_version": version,
        "archive": ARCHIVE_NAME,
        "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "exercise_count": len(entries),
        "media_count": len(media),
        "license": "MIT data; media terms in NOTICE.md",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args()
    build_release(Path.cwd(), args.output, args.version)


if __name__ == "__main__":
    main()
