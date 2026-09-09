from fastmcp import FastMCP
from mcp_server.database import get_connection

def register_order_tools(mcp: FastMCP):

    @mcp.tool()
    def get_order_trends(
        start_date: str,
        end_date: str,
        metrics: list[str],
        group_by: str,
    ) -> dict:
        """
        Get order and revenue trends over time.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            metrics: Metrics to calculate:
                     revenue, order_count, average_order_value.
            group_by: Time grouping:
                      day, week, month, year.
        """

        allowed_metrics = {
            "revenue",
            "order_count",
            "average_order_value",
        }

        allowed_groupings = {
            "day",
            "week",
            "month",
            "year",
        }

        if not metrics:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "At least one metric must be provided.",
                },
            }

        invalid_metrics = set(metrics) - allowed_metrics

        if invalid_metrics:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": (
                        f"Invalid metrics: {sorted(invalid_metrics)}. "
                        f"Allowed values: {sorted(allowed_metrics)}"
                    ),
                },
            }

        if group_by not in allowed_groupings:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": (
                        f"Invalid group_by: '{group_by}'. "
                        f"Allowed values: {sorted(allowed_groupings)}"
                    ),
                },
            }

        if start_date > end_date:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_DATE_RANGE",
                    "message": (
                        "start_date must be before or equal to end_date."
                    ),
                },
            }

        date_formats = {
            "day": "%Y-%m-%d",
            "month": "%Y-%m",
            "year": "%Y",
        }

        if group_by == "week":
            date_expression = (
                "strftime('%Y-%W', o.order_purchase_timestamp)"
            )
        else:
            date_expression = (
                f"strftime('{date_formats[group_by]}', "
                "o.order_purchase_timestamp)"
            )

        metric_expressions = []

        if "order_count" in metrics:
            metric_expressions.append(
                "COUNT(DISTINCT o.order_id) AS order_count"
            )

        if "revenue" in metrics:
            metric_expressions.append(
                "COALESCE(SUM(p.payment_value), 0) AS revenue"
            )

        if "average_order_value" in metrics:
            metric_expressions.append(
                """
                COALESCE(
                    SUM(p.payment_value) /
                    NULLIF(COUNT(DISTINCT o.order_id), 0),
                    0
                ) AS average_order_value
                """.strip()
            )

        select_metrics = ",\n        ".join(metric_expressions)

        query = f"""
            SELECT
                {date_expression} AS period,
                {select_metrics}
            FROM orders o
            LEFT JOIN order_payments p
                ON o.order_id = p.order_id
            WHERE date(o.order_purchase_timestamp)
                  BETWEEN date(?) AND date(?)
            GROUP BY period
            ORDER BY period;
        """

        try:
            with get_connection() as connection:
                rows = connection.execute(
                    query,
                    (start_date, end_date),
                ).fetchall()

                data = [dict(row) for row in rows]

        except Exception as exc:
            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": str(exc),
                },
            }

        if not data:
            return {
                "success": False,
                "error": {
                    "code": "NO_RESULTS",
                    "message": (
                        "No orders were found for the specified date range."
                    ),
                },
            }

        return {
            "success": True,
            "data": data,
            "metadata": {
                "row_count": len(data),
                "start_date": start_date,
                "end_date": end_date,
                "group_by": group_by,
                "metrics": metrics,
            },
        }