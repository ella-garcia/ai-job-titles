"""Append-safe JSON-lines files.

Collectors append one record per line as they go. If a run is interrupted mid-write, the file may end
with a partial line (or, for gzip, a truncated block); readers skip that instead of failing, so
everything written before the interruption is kept.
"""
import gzip
import json
import zlib
from pathlib import Path


def read_lenient(path: Path) -> list[dict]:
    records = []
    opener = gzip.open if path.name.endswith(".gz") else open
    try:
        with opener(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # partial last line from an interrupted write
    except (EOFError, zlib.error, gzip.BadGzipFile):
        pass  # truncated gzip: keep the records read so far
    return records


def append(path: Path, record: dict) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
