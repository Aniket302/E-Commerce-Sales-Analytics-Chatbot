from dashboard.models import PinnedChart
from dashboard.storage import (
    create_pinned_chart,
    list_pinned_charts,
    get_pinned_chart,
    update_pinned_chart,
    delete_pinned_chart,
)
from dashboard.change_detection import detect_significant_change


def pin_query_result(query: str, result: dict) -> PinnedChart:
    if not result.get("success"):
        raise ValueError("Cannot pin an unsuccessful query result.")

    chart = result.get("chart")
    if not chart or not chart.get("type"):
        raise ValueError("Cannot pin a result without a chart.")

    data = result.get("data")
    if not data or not data.get("data"):
        raise ValueError("Cannot pin a result with no data.")

    tool_name = result.get("tool")
    arguments = result.get("arguments")

    if not tool_name:
        raise ValueError("Cannot pin a result without a tool name.")

    if not arguments:
        raise ValueError("Cannot pin a result without tool arguments.")

    return create_pinned_chart(
        query=query,
        tool_name=tool_name,
        arguments=arguments,
        chart=chart,
        data=data,
    )


def get_dashboard() -> list[PinnedChart]:
    return list_pinned_charts()


async def refresh_pinned_chart(
    chart_id: int,
    agent,
) -> dict:
    pinned_chart = get_pinned_chart(chart_id)

    if pinned_chart is None:
        raise ValueError(f"Pinned chart {chart_id} was not found.")

    old_data = pinned_chart.data

    # Re-run the original query.
    new_result = await agent.ask(pinned_chart.query)

    if not new_result.get("success"):
        return {
            "success": False,
            "chart_id": chart_id,
            "error": "The original query failed during refresh.",
            "change_detection": {
                "significant": False,
                "changes": [],
            },
        }

    new_data = new_result.get("data")
    new_chart = new_result.get("chart")

    if not new_data or not new_data.get("data"):
        return {
            "success": False,
            "chart_id": chart_id,
            "error": "The refreshed query returned no data.",
            "change_detection": {
                "significant": False,
                "changes": [],
            },
        }

    change_detection = detect_significant_change(
        old_data=old_data,
        new_data=new_data,
        chart=new_chart or pinned_chart.chart,
    )

    updated_chart = update_pinned_chart(
        chart_id=chart_id,
        data=new_data,
        chart=new_chart or pinned_chart.chart,
    )

    return {
        "success": True,
        "chart_id": chart_id,
        "chart": updated_chart.__dict__ if updated_chart else None,
        "change_detection": change_detection,
    }

def unpin_chart(chart_id: int) -> bool:
    return delete_pinned_chart(chart_id)