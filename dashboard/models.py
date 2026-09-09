from dataclasses import dataclass
from typing import Any


@dataclass
class PinnedChart:
    id: int | None
    query: str
    tool_name: str
    arguments: dict[str, Any]
    chart: dict[str, Any]
    data: dict[str, Any]
    created_at: str
    last_refreshed_at: str