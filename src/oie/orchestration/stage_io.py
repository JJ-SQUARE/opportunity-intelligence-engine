from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def write_json_file(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_json_file(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl_item(path: Path, item: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as output_file:
        output_file.write(json.dumps(item, ensure_ascii=False) + "\n")


def read_jsonl_file(path: Path) -> list[Dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
