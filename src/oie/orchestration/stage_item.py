from __future__ import annotations

from typing import NotRequired, TypedDict

from oie.orchestration.json_payload import JSONPayload


class StageItem(TypedDict, total=False):
    id: NotRequired[str]
    value: NotRequired[object]
    metadata: NotRequired[JSONPayload]
