from typing import Any


def calculate_relative_change(old_value: float, new_value: float) -> float:
    if old_value == 0:
        if new_value == 0:
            return 0.0
        return 100.0

    return abs((new_value - old_value) / old_value) * 100


def detect_significant_change(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
    chart: dict[str, Any] | None = None,
    threshold: float = 10.0,
) -> dict[str, Any]:

    old_rows = old_data.get("data", [])
    new_rows = new_data.get("data", [])

    if not old_rows or not new_rows:
        return {
            "significant": False,
            "changes": [],
            "reason": "Insufficient data for comparison.",
        }

    # Use the chart's x-axis as the row identity.
    x_field = chart.get("x") if chart else None

    # Determine which fields are actual metrics.
    y_fields = []

    if chart:
        y_value = chart.get("y")

        if isinstance(y_value, list):
            y_fields = y_value
        elif isinstance(y_value, str):
            y_fields = [y_value]

    # Fallback for charts without a clear x/y specification.
    if not x_field:
        x_field = "period"

    if not y_fields:
        numeric_fields = set()

        for row in old_rows:
            for field, value in row.items():
                if isinstance(value, (int, float)):
                    numeric_fields.add(field)

        y_fields = list(numeric_fields)

    old_by_key = {
        row.get(x_field): row
        for row in old_rows
    }

    new_by_key = {
        row.get(x_field): row
        for row in new_rows
    }

    common_keys = old_by_key.keys() & new_by_key.keys()

    changes = []

    for key in common_keys:
        old_row = old_by_key[key]
        new_row = new_by_key[key]

        for field in y_fields:

            if field not in old_row or field not in new_row:
                continue

            old_value = old_row[field]
            new_value = new_row[field]

            if not isinstance(old_value, (int, float)):
                continue

            if not isinstance(new_value, (int, float)):
                continue

            if old_value == new_value:
                continue

            percentage_change = calculate_relative_change(
                float(old_value),
                float(new_value),
            )

            if percentage_change >= threshold:
                changes.append(
                    {
                        "key": {
                            x_field: key
                        },
                        "field": field,
                        "old_value": old_value,
                        "new_value": new_value,
                        "percentage_change": round(
                            percentage_change,
                            2,
                        ),
                    }
                )

    return {
        "significant": len(changes) > 0,
        "changes": changes,
        "threshold_percentage": threshold,
    }