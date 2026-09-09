import re
from typing import Any


def identify_analysis_type(user_query: str) -> str | None:
    """
    Identify known multi-tool analysis patterns.
    """
    query = user_query.lower()

    if (
        "category" in query
        and ("review" in query or "rating" in query)
        and ("sales" in query or "volume" in query or "orders" in query)
    ):
        return "category_volume_review"

    if (
        ("monthly" in query or "by month" in query)
        and ("order" in query or "orders" in query)
        and ("review" in query or "rating" in query)
    ):
        return "monthly_orders_review"

    if (
        "seller" in query
        and ("delivery" in query or "delivered" in query)
        and ("review" in query or "rating" in query)
    ):
        return "seller_delivery_review"

    if (
        ("state" in query or "states" in query)
        and ("delivery" in query or "delay" in query)
        and ("review" in query or "rating" in query)
    ):
        return "state_delivery_review"

    return None


def extract_top_n(user_query: str, default: int = 10) -> int:
    """
    Extract 'top N' from a query.
    """
    match = re.search(r"\btop\s+(\d+)\b", user_query.lower())

    if match:
        return int(match.group(1))

    return default


def _successful_results(tool_results: list[dict]) -> list[dict]:
    return [
        result
        for result in tool_results
        if result.get("success", True)
    ]


def _find_result(
    tool_results: list[dict],
    tool_name: str,
) -> dict | None:
    for result in tool_results:
        if result.get("tool") == tool_name and result.get("success", True):
            return result

    return None


def _result_data(result: dict | None) -> list[dict]:
    if not result:
        return []

    data = result.get("data", [])

    return data if isinstance(data, list) else []


def build_required_tool_calls(
    analysis_type: str | None,
    user_query: str,
) -> list[dict[str, Any]]:
    """
    Build a deterministic first-stage plan for known multi-tool analyses.

    The LLM still performs native tool calling for normal queries.
    This planner acts as a guardrail for complex dependent analyses.
    """

    if analysis_type == "category_volume_review":
        limit = extract_top_n(user_query, default=10)

        return [
            {
                "tool": "get_category_performance",
                "arguments": {
                    "start_date": "2016-01-01",
                    "end_date": "2018-12-31",
                    "metric": "order_count",
                    "limit": limit,
                    "sort": "desc",
                },
            }
        ]

    if analysis_type == "monthly_orders_review":
        return [
            {
                "tool": "get_order_trends",
                "arguments": {
                    "start_date": "2016-01-01",
                    "end_date": "2018-12-31",
                    "metrics": ["order_count"],
                    "group_by": "month",
                }
            }
        ]

    if analysis_type == "seller_delivery_review":
        return [
            {
                "tool": "get_seller_performance",
                "arguments": {
                    "start_date": "2016-01-01",
                    "end_date": "2018-12-31",
                    "metrics": [
                        "average_delivery_days",
                        "average_review_score",
                    ],
                    "limit": None,
                    "sort": "desc",
                }
            }
        ]

    if analysis_type == "state_delivery_review":
        return [
            {
                "tool": "get_delivery_performance",
                "arguments": {
                    "start_date": "2016-01-01",
                    "end_date": "2018-12-31",
                    "metric": "average_delay_days",
                    "group_by": "customer_state",
                    "limit": 100,
                    "sort": "desc",
                }
            }
        ]

    return []


def build_dependent_tool_calls(
    analysis_type: str | None,
    tool_results: list[dict],
) -> list[dict[str, Any]]:
    """
    Build second-stage tool calls using results from the first stage.
    """

    calls = []

    if analysis_type == "category_volume_review":

        category_result = _find_result(
            tool_results,
            "get_category_performance",
        )

        categories = []

        for row in _result_data(category_result):
            category = row.get("category")

            if category:
                categories.append(category)

        if categories and category_result:
            args = category_result.get("arguments", {})

            calls.append(
                {
                    "tool": "get_category_performance",
                    "arguments": {
                        "start_date": args.get(
                            "start_date",
                            "2016-01-01",
                        ),
                        "end_date": args.get(
                            "end_date",
                            "2018-12-31",
                        ),
                        "metric": "average_review_score",
                        "categories": categories,
                        "limit": len(categories),
                        "sort": "desc",
                    },
                }
            )

    elif analysis_type == "monthly_orders_review":

        order_result = _find_result(
            tool_results,
            "get_order_trends",
        )

        if order_result:
            args = order_result.get("arguments", {})

            calls.append(
                {
                    "tool": "get_review_analysis",
                    "arguments": {
                        "start_date": args.get(
                            "start_date",
                            "2016-01-01",
                        ),
                        "end_date": args.get(
                            "end_date",
                            "2018-12-31",
                        ),
                        "metric": "average_review_score",
                        "group_by": "month",
                        "limit": 100,
                        "sort": "asc",
                    },
                }
            )

    elif analysis_type == "state_delivery_review":

        delivery_result = _find_result(
            tool_results,
            "get_delivery_performance",
        )

        if delivery_result:
            args = delivery_result.get("arguments", {})

            calls.append(
                {
                    "tool": "get_review_analysis",
                    "arguments": {
                        "start_date": args.get(
                            "start_date",
                            "2016-01-01",
                        ),
                        "end_date": args.get(
                            "end_date",
                            "2018-12-31",
                        ),
                        "metric": "average_review_score",
                        "group_by": "customer_state",
                        "limit": 100,
                        "sort": "desc",
                    },
                }
            )

    return calls


def calculate_pearson_correlation(
    rows: list[dict],
    x_key: str,
    y_key: str,
) -> float | None:

    pairs = []

    for row in rows:
        try:
            x = float(row[x_key])
            y = float(row[y_key])
            pairs.append((x, y))
        except (KeyError, TypeError, ValueError):
            continue

    if len(pairs) < 2:
        return None

    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]

    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)

    numerator = sum(
        (x - x_mean) * (y - y_mean)
        for x, y in pairs
    )

    x_variance = sum(
        (x - x_mean) ** 2
        for x in xs
    )

    y_variance = sum(
        (y - y_mean) ** 2
        for y in ys
    )

    denominator = (x_variance * y_variance) ** 0.5

    if denominator == 0:
        return None

    return numerator / denominator


def build_multi_tool_analysis(
    analysis_type: str | None,
    tool_results: list[dict],
) -> dict:

    if analysis_type == "category_volume_review":

        volume_result = _find_result(
            tool_results,
            "get_category_performance",
        )

        review_results = [
            result
            for result in tool_results
            if (
                result.get("tool") == "get_category_performance"
                and result.get("arguments", {}).get("metric")
                == "average_review_score"
            )
        ]

        review_result = review_results[-1] if review_results else None

        volume_rows = _result_data(volume_result)
        review_rows = _result_data(review_result)

        review_by_category = {
            row.get("category"): row
            for row in review_rows
            if row.get("category")
        }

        combined = []

        for row in volume_rows:
            category = row.get("category")

            if not category:
                continue

            review = review_by_category.get(category, {})

            combined.append(
                {
                    "category": category,
                    "order_count": row.get("order_count", 0),
                    "average_review_score": review.get(
                        "average_review_score"
                    ),
                }
            )

        return {
            "analysis_type": analysis_type,
            "data": combined,
            "success": bool(combined),
        }

    if analysis_type == "monthly_orders_review":

        order_result = _find_result(
            tool_results,
            "get_order_trends",
        )

        review_results = [
            result
            for result in tool_results
            if (
                result.get("tool") == "get_review_analysis"
                and result.get("arguments", {}).get("group_by")
                == "month"
            )
        ]

        review_result = review_results[-1] if review_results else None

        order_rows = _result_data(order_result)
        review_rows = _result_data(review_result)

        review_by_period = {
            row.get("period"): row
            for row in review_rows
            if row.get("period")
        }

        combined = []

        for row in order_rows:
            period = row.get("period")

            if not period:
                continue

            review = review_by_period.get(period, {})

            combined.append(
                {
                    "period": period,
                    "order_count": row.get("order_count", 0),
                    "average_review_score": review.get(
                        "average_review_score"
                    ),
                }
            )

        combined.sort(key=lambda row: row["period"])

        return {
            "analysis_type": analysis_type,
            "data": combined,
            "success": bool(combined),
        }

    if analysis_type == "seller_delivery_review":

        seller_result = _find_result(
            tool_results,
            "get_seller_performance",
        )

        rows = _result_data(seller_result)

        correlation = calculate_pearson_correlation(
            rows,
            "average_delivery_days",
            "average_review_score",
        )

        combined = [
            {
                "seller_id": row.get("seller_id"),
                "average_delivery_days": row.get(
                    "average_delivery_days"
                ),
                "average_review_score": row.get(
                    "average_review_score"
                ),
            }
            for row in rows
        ]

        return {
            "analysis_type": analysis_type,
            "data": combined,
            "correlation": correlation,
            "success": bool(combined),
        }

    if analysis_type == "state_delivery_review":

        delivery_result = _find_result(
            tool_results,
            "get_delivery_performance",
        )

        review_results = [
            result
            for result in tool_results
            if (
                result.get("tool") == "get_review_analysis"
                and result.get("arguments", {}).get("group_by")
                == "customer_state"
            )
        ]

        review_result = review_results[-1] if review_results else None

        delivery_rows = _result_data(delivery_result)
        review_rows = _result_data(review_result)

        review_by_state = {
            row.get("customer_state"): row
            for row in review_rows
            if row.get("customer_state")
        }

        combined = []

        for row in delivery_rows:
            state = row.get("customer_state")

            if not state:
                continue

            review = review_by_state.get(state, {})

            combined.append(
                {
                    "customer_state": state,
                    "average_delay_days": row.get(
                        "average_delay_days"
                    ),
                    "average_review_score": review.get(
                        "average_review_score"
                    ),
                }
            )

        return {
            "analysis_type": analysis_type,
            "data": combined,
            "success": bool(combined),
        }

    return {
        "analysis_type": None,
        "data": [],
        "success": False,
    }