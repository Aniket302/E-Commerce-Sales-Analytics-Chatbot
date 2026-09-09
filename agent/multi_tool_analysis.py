from typing import Any


def _safe_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _index_by(rows: list[dict], key: str) -> dict:
    return {
        row[key]: row
        for row in rows
        if row.get(key) is not None
    }


def compare_category_volume_and_reviews(
    volume_rows: list[dict],
    review_rows: list[dict],
) -> list[dict]:

    reviews = _index_by(review_rows, "category")

    result = []

    for row in volume_rows:

        category = row.get("category")

        if category not in reviews:
            continue

        result.append({
            "category": category,
            "order_count": row.get("order_count"),
            "average_review_score": reviews[category].get(
                "average_review_score"
            ),
        })

    return result


def compare_monthly_orders_and_reviews(
    order_rows: list[dict],
    review_rows: list[dict],
) -> list[dict]:

    reviews = _index_by(review_rows, "month")

    result = []

    for row in order_rows:

        month = row.get("period")

        if month not in reviews:
            continue

        result.append({
            "month": month,
            "order_count": row.get("order_count"),
            "average_review_score": reviews[month].get(
                "average_review_score"
            ),
        })

    return result


def compare_seller_delivery_and_reviews(
    seller_rows: list[dict],
) -> list[dict]:

    result = []

    for row in seller_rows:

        delivery_days = _safe_float(
            row.get("average_delivery_days")
        )

        review_score = _safe_float(
            row.get("average_review_score")
        )

        if delivery_days is None or review_score is None:
            continue

        result.append({
            "seller_id": row.get("seller_id"),
            "average_delivery_days": delivery_days,
            "average_review_score": review_score,
        })

    return result


def compare_state_delivery_and_reviews(
    delivery_rows: list[dict],
    review_rows: list[dict],
) -> list[dict]:

    reviews = _index_by(
        review_rows,
        "customer_state"
    )

    result = []

    for row in delivery_rows:

        state = row.get("customer_state")

        if state not in reviews:
            continue

        result.append({
            "customer_state": state,
            "average_delay_days": row.get(
                "average_delay_days"
            ),
            "average_review_score": reviews[state].get(
                "average_review_score"
            ),
        })

    return result


def calculate_pearson_correlation(
    rows: list[dict],
    x_key: str,
    y_key: str,
):
    """
    Calculate Pearson correlation between two numeric variables.

    Returns:
        float | None
    """

    values = []

    for row in rows:

        x = _safe_float(row.get(x_key))
        y = _safe_float(row.get(y_key))

        if x is not None and y is not None:
            values.append((x, y))

    if len(values) < 2:
        return None

    x_values = [x for x, _ in values]
    y_values = [y for _, y in values]

    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)

    numerator = sum(
        (x - x_mean) * (y - y_mean)
        for x, y in values
    )

    x_variance = sum(
        (x - x_mean) ** 2
        for x in x_values
    )

    y_variance = sum(
        (y - y_mean) ** 2
        for y in y_values
    )

    denominator = (
        x_variance * y_variance
    ) ** 0.5

    if denominator == 0:
        return None

    return numerator / denominator