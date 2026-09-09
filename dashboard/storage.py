import json
from datetime import datetime, timezone

from mcp_server.database import get_connection

from dashboard.models import PinnedChart


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_pinned_chart(
    query: str,
    tool_name: str,
    arguments: dict,
    chart: dict,
    data: dict,
) -> PinnedChart:

    now = _now()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO pinned_charts (
                query,
                tool_name,
                arguments_json,
                chart_json,
                data_json,
                created_at,
                last_refreshed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query,
                tool_name,
                json.dumps(arguments),
                json.dumps(chart),
                json.dumps(data),
                now,
                now,
            ),
        )

        chart_id = cursor.lastrowid

    return PinnedChart(
        id=chart_id,
        query=query,
        tool_name=tool_name,
        arguments=arguments,
        chart=chart,
        data=data,
        created_at=now,
        last_refreshed_at=now,
    )

def _row_to_pinned_chart(row) -> PinnedChart:
    return PinnedChart(
        id=row["id"],
        query=row["query"],
        tool_name=row["tool_name"],
        arguments=json.loads(row["arguments_json"]),
        chart=json.loads(row["chart_json"]),
        data=json.loads(row["data_json"]),
        created_at=row["created_at"],
        last_refreshed_at=row["last_refreshed_at"],
    )


def get_pinned_chart(chart_id: int) -> PinnedChart | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                query,
                tool_name,
                arguments_json,
                chart_json,
                data_json,
                created_at,
                last_refreshed_at
            FROM pinned_charts
            WHERE id = ?
            """,
            (chart_id,),
        ).fetchone()

    if row is None:
        return None

    return _row_to_pinned_chart(row)


def list_pinned_charts() -> list[PinnedChart]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                query,
                tool_name,
                arguments_json,
                chart_json,
                data_json,
                created_at,
                last_refreshed_at
            FROM pinned_charts
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [_row_to_pinned_chart(row) for row in rows]

def update_pinned_chart(
    chart_id: int,
    data: dict,
    chart: dict,
) -> PinnedChart | None:
    now = _now()

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE pinned_charts
            SET data_json = ?,
                chart_json = ?,
                last_refreshed_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(data),
                json.dumps(chart),
                now,
                chart_id,
            ),
        )

    return get_pinned_chart(chart_id)

def delete_pinned_chart(chart_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM pinned_charts WHERE id = ?",
            (chart_id,),
        )

    return cursor.rowcount > 0