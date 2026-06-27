from __future__ import annotations

import json
from pathlib import Path

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.stage_item import StageItem


def write_json_file(path: Path, payload: JSONPayload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def read_json_file(path: Path) -> JSONPayload | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl_item(path: Path, item: StageItem) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output_file:
        output_file.write(json.dumps(item, ensure_ascii=False) + "\n")


def read_jsonl_file(path: Path) -> list[StageItem]:
    if not path.exists():
        return []

    items = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
    return items
