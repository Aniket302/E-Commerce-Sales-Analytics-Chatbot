from fastmcp import FastMCP
from mcp_server.database import get_connection

def register_delivery_tools(mcp: FastMCP):

    @mcp.tool
    def get_delivery_performance(
        start_date: str,
        end_date: str,
        metric: str,
        group_by: str = "month",
        limit: int = 10,
        sort: str = "desc",
    ) -> dict:
        """
        Analyze delivery performance over a specified date range.

        Supported metrics:
        - average_delivery_days
        - average_delay_days
        - on_time_rate
        - order_count

        Supported group_by:
        - month
        - seller_state
        - customer_state
        - route

        For route analysis, route represents seller_state -> customer_state.
        """

        # -----------------------------
        # Validate inputs
        # -----------------------------

        valid_metrics = {
            "average_delivery_days",
            "average_delay_days",
            "on_time_rate",
            "order_count",
        }

        valid_groupings = {
            "month",
            "seller_state",
            "customer_state",
            "route",
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
        # Metric expression
        # -----------------------------

        metric_expressions = {

            "average_delivery_days": """
                AVG(
                    julianday(order_delivered_customer_date)
                    - julianday(order_purchase_timestamp)
                )
            """,

            "average_delay_days": """
                AVG(
                    julianday(order_delivered_customer_date)
                    - julianday(order_estimated_delivery_date)
                )
            """,

            "on_time_rate": """
                100.0 * AVG(
                    CASE
                        WHEN
                            julianday(order_delivered_customer_date)
                            <= julianday(order_estimated_delivery_date)
                        THEN 1.0
                        ELSE 0.0
                    END
                )
            """,

            "order_count": """
                COUNT(DISTINCT order_id)
            """,
        }

        metric_expression = metric_expressions[metric]

        # ============================================================
        # CASE 1: Monthly / Customer-state analysis
        #
        # These metrics can be calculated directly at order level.
        # ============================================================

        if group_by == "month":

            group_expression = """
                strftime('%Y-%m', order_purchase_timestamp)
            """

            select_group = """
                strftime('%Y-%m', order_purchase_timestamp) AS group_name
            """

            query = f"""
                SELECT
                    {select_group},
                    {metric_expression} AS value

                FROM orders

                WHERE
                    DATE(order_purchase_timestamp)
                    BETWEEN DATE(?) AND DATE(?)

                    AND order_delivered_customer_date IS NOT NULL

                    AND order_estimated_delivery_date IS NOT NULL

                GROUP BY
                    {group_expression}

                ORDER BY
                    group_name ASC
            """

            params = [start_date, end_date]

        elif group_by == "customer_state":

            query = f"""
                SELECT
                    c.customer_state AS group_name,
                    {metric_expression} AS value

                FROM orders o

                JOIN customers c
                    ON o.customer_id = c.customer_id

                WHERE
                    DATE(o.order_purchase_timestamp)
                    BETWEEN DATE(?) AND DATE(?)

                    AND o.order_delivered_customer_date IS NOT NULL

                    AND o.order_estimated_delivery_date IS NOT NULL

                GROUP BY
                    c.customer_state

                ORDER BY
                    value {sort.upper()}

                LIMIT ?
            """

            params = [start_date, end_date, limit]

        # ============================================================
        # CASE 2: Seller-state / Route analysis
        #
        # An order can contain multiple sellers.
        # We therefore use DISTINCT order + seller combinations.
        # ============================================================

        else:

            if group_by == "seller_state":

                select_group = """
                    s.seller_state AS group_name
                """

                group_expression = """
                    s.seller_state
                """

            else:

                select_group = """
                    s.seller_state || ' -> ' || c.customer_state
                    AS group_name
                """

                group_expression = """
                    s.seller_state,
                    c.customer_state
                """

            query = f"""
                WITH order_sellers AS (

                    SELECT DISTINCT
                        oi.order_id,
                        oi.seller_id

                    FROM order_items oi
                )

                SELECT
                    {select_group},
                    {metric_expression} AS value

                FROM order_sellers os

                JOIN orders o
                    ON os.order_id = o.order_id

                JOIN sellers s
                    ON os.seller_id = s.seller_id

                JOIN customers c
                    ON o.customer_id = c.customer_id

                WHERE
                    DATE(o.order_purchase_timestamp)
                    BETWEEN DATE(?) AND DATE(?)

                    AND o.order_delivered_customer_date IS NOT NULL

                    AND o.order_estimated_delivery_date IS NOT NULL

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