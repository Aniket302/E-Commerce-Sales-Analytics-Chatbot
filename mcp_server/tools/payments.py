from fastmcp import FastMCP
from mcp_server.database import get_connection

def register_payment_tools(mcp: FastMCP):

    @mcp.tool
    def get_payment_breakdown(
        start_date: str,
        end_date: str,
        metric: str,
        group_by: str = "payment_type",
        limit: int = 10,
        sort: str = "desc",
    ) -> dict:
        """
        Analyze payment methods and payment values over a date range.

        Supported metrics:
        - payment_value
        - payment_count
        - average_installments

        Supported group_by:
        - payment_type
        - month
        """

        # -----------------------------
        # Validate inputs
        # -----------------------------

        valid_metrics = {
            "payment_value",
            "payment_count",
            "average_installments",
        }

        valid_groupings = {
            "payment_type",
            "month",
        }

        if metric not in valid_metrics:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_METRIC",
                    "message": (
                        f"Unsupported metric '{metric}'. "
                        f"Supported metrics: {sorted(valid_metrics)}"
                    ),
                },
            }

        if group_by not in valid_groupings:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_GROUP_BY",
                    "message": (
                        f"Unsupported group_by '{group_by}'. "
                        f"Supported values: {sorted(valid_groupings)}"
                    ),
                },
            }

        if sort not in {"asc", "desc"}:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_SORT",
                    "message": "sort must be either 'asc' or 'desc'.",
                },
            }

        if limit < 1 or limit > 100:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_LIMIT",
                    "message": "limit must be between 1 and 100.",
                },
            }

        if start_date > end_date:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_DATE_RANGE",
                    "message": "start_date must be before or equal to end_date.",
                },
            }

        # -----------------------------
        # Determine grouping
        # -----------------------------

        if group_by == "payment_type":
            group_expression = "op.payment_type"
            select_group = "op.payment_type AS group_name"

        else:
            group_expression = "strftime('%Y-%m', o.order_purchase_timestamp)"
            select_group = (
                "strftime('%Y-%m', o.order_purchase_timestamp) AS group_name"
            )

        # -----------------------------
        # Determine metric
        # -----------------------------

        metric_expressions = {
            "payment_value": "SUM(op.payment_value)",
            "payment_count": "COUNT(*)",
            "average_installments": "AVG(op.payment_installments)",
        }

        metric_expression = metric_expressions[metric]

        # -----------------------------
        # Build query
        # -----------------------------

        query = f"""
            SELECT
                {select_group},
                {metric_expression} AS value

            FROM order_payments op

            JOIN orders o
                ON op.order_id = o.order_id

            WHERE
                DATE(o.order_purchase_timestamp)
                BETWEEN DATE(?) AND DATE(?)

            GROUP BY
                {group_expression}

            ORDER BY
                value {sort.upper()}

            LIMIT ?
        """

        params = [start_date, end_date, limit]

        # -----------------------------
        # Execute query
        # -----------------------------

        try:

            connection = get_connection()

            rows = connection.execute(
                query,
                params
            ).fetchall()

            connection.close()

            data = []

            for row in rows:

                data.append({
                    group_by: row["group_name"],
                    metric: row["value"],
                })

            return {
                "success": True,
                "data": data,
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "metric": metric,
                    "group_by": group_by,
                    "limit": limit,
                    "sort": sort,
                    "row_count": len(data),
                },
            }

        except Exception as e:

            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": str(e),
                },
            }