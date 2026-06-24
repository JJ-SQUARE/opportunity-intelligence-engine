from __future__ import annotations

import json
from pathlib import Path

from oie.orchestration.json_payload import JSONPayload
from oie.orchestration.stage_item import StageItem


def write_json_file(path: Path, payload: JSONPayload) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_json_file(path: Path) -> JSONPayload | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl_item(path: Path, item: StageItem) -> None:
    with path.open("a", encoding="utf-8") as output_file:
        output_file.write(json.dumps(item, ensure_ascii=False) + "\n")


def read_jsonl_file(path: Path) -> list[StageItem]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
