from fastmcp import FastMCP
from mcp_server.database import get_connection


def register_seller_tools(mcp: FastMCP):

    @mcp.tool()
    def get_seller_performance(
        start_date: str,
        end_date: str,
        metric: str | None = None,
        metrics: list[str] | None = None,
        state: str | None = None,
        limit: int | None = 10,
        sort: str = "desc",
    ) -> dict:
        """
        Analyze seller performance over a specified date range.

        Supported metrics:
        - revenue
        - order_count
        - average_review_score
        - average_delivery_days

        Use either:
        - metric for a single metric
        - metrics for multiple metrics

        Optional state filter uses Brazilian state codes such as SP, RJ, MG.

        When metrics contains multiple values, all metrics are returned
        at the same seller level so they can be compared directly.
        """

        valid_metrics = {
            "revenue",
            "order_count",
            "average_review_score",
            "average_delivery_days",
        }

        # ---------------------------------------------------------
        # Resolve requested metrics
        # ---------------------------------------------------------

        if metrics is None:

            if metric is None:
                return {
                    "success": False,
                    "error": {
                        "code": "MISSING_METRIC",
                        "message": (
                            "Provide either 'metric' or 'metrics'."
                        ),
                    },
                }

            requested_metrics = [metric]

        else:

            if not metrics:
                return {
                    "success": False,
                    "error": {
                        "code": "EMPTY_METRICS",
                        "message": "metrics must contain at least one metric.",
                    },
                }

            requested_metrics = metrics

        # Remove duplicates while preserving order.
        requested_metrics = list(dict.fromkeys(requested_metrics))

        invalid_metrics = [
            item
            for item in requested_metrics
            if item not in valid_metrics
        ]

        if invalid_metrics:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_METRIC",
                    "message": (
                        f"Unsupported metrics: {invalid_metrics}. "
                        f"Supported metrics: {sorted(valid_metrics)}"
                    ),
                },
            }

        # ---------------------------------------------------------
        # Validate other inputs
        # ---------------------------------------------------------

        if sort not in {"asc", "desc"}:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_SORT",
                    "message": "sort must be either 'asc' or 'desc'.",
                },
            }

        if limit is not None and (limit < 1 or limit > 3095):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_LIMIT",
                    "message": "limit must be between 1 and 3095.",
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

        # ---------------------------------------------------------
        # Build common seller/order base
        # ---------------------------------------------------------

        query = """
            WITH seller_orders AS (
                SELECT DISTINCT
                    oi.seller_id,
                    oi.order_id
                FROM order_items oi
                JOIN orders o
                    ON oi.order_id = o.order_id
                WHERE date(o.order_purchase_timestamp)
                      BETWEEN date(?) AND date(?)
            ),

            order_review_scores AS (
                SELECT
                    r.order_id,
                    AVG(r.review_score) AS review_score
                FROM order_reviews r
                GROUP BY r.order_id
            )

            SELECT
                s.seller_id,
                s.seller_city,
                s.seller_state
        """

        params = [start_date, end_date]

        # ---------------------------------------------------------
        # Add requested metrics
        # ---------------------------------------------------------

        if "revenue" in requested_metrics:

            query += """
                ,
                seller_revenue AS (
                    SELECT
                        oi.seller_id,
                        ROUND(SUM(oi.price), 2) AS revenue
                    FROM order_items oi
                    JOIN orders o
                        ON oi.order_id = o.order_id
                    WHERE date(o.order_purchase_timestamp)
                          BETWEEN date(?) AND date(?)
                    GROUP BY oi.seller_id
                )
            """

            params.extend([start_date, end_date])

            query += """
                ,
                seller_revenue_joined AS (
                    SELECT
                        seller_id,
                        revenue
                    FROM seller_revenue
                )
            """

        # ---------------------------------------------------------
        # We construct the final SELECT separately because
        # SQLite CTE ordering is easier to maintain this way.
        # ---------------------------------------------------------

        # Rebuild the query using a single comprehensive CTE.
        query = """
            WITH seller_orders AS (
                SELECT DISTINCT
                    oi.seller_id,
                    oi.order_id
                FROM order_items oi
                JOIN orders o
                    ON oi.order_id = o.order_id
                WHERE date(o.order_purchase_timestamp)
                      BETWEEN date(?) AND date(?)
            ),

            seller_revenue AS (
                SELECT
                    oi.seller_id,
                    ROUND(SUM(oi.price), 2) AS revenue
                FROM order_items oi
                JOIN orders o
                    ON oi.order_id = o.order_id
                WHERE date(o.order_purchase_timestamp)
                      BETWEEN date(?) AND date(?)
                GROUP BY oi.seller_id
            ),

            seller_order_counts AS (
                SELECT
                    seller_id,
                    COUNT(DISTINCT order_id) AS order_count
                FROM seller_orders
                GROUP BY seller_id
            ),

            order_review_scores AS (
                SELECT
                    r.order_id,
                    AVG(r.review_score) AS review_score
                FROM order_reviews r
                GROUP BY r.order_id
            ),

            seller_reviews AS (
                SELECT
                    so.seller_id,
                    ROUND(AVG(ors.review_score), 2)
                        AS average_review_score
                FROM seller_orders so
                JOIN order_review_scores ors
                    ON so.order_id = ors.order_id
                GROUP BY so.seller_id
            ),

            seller_delivery AS (
                SELECT
                    so.seller_id,
                    ROUND(
                        AVG(
                            julianday(
                                o.order_delivered_customer_date
                            )
                            -
                            julianday(
                                o.order_purchase_timestamp
                            )
                        ),
                        2
                    ) AS average_delivery_days
                FROM seller_orders so
                JOIN orders o
                    ON so.order_id = o.order_id
                WHERE o.order_delivered_customer_date IS NOT NULL
                GROUP BY so.seller_id
            )

            SELECT
                s.seller_id,
                s.seller_city,
                s.seller_state
        """

        params = [
            start_date,
            end_date,
            start_date,
            end_date,
        ]

        # ---------------------------------------------------------
        # Select requested metrics
        # ---------------------------------------------------------

        if "revenue" in requested_metrics:
            query += """
                ,
                sr.revenue AS revenue
            """

        if "order_count" in requested_metrics:
            query += """
                ,
                soc.order_count AS order_count
            """

        if "average_review_score" in requested_metrics:
            query += """
                ,
                sv.average_review_score AS average_review_score
            """

        if "average_delivery_days" in requested_metrics:
            query += """
                ,
                sd.average_delivery_days AS average_delivery_days
            """

        query += """
            FROM sellers s

            LEFT JOIN seller_revenue sr
                ON s.seller_id = sr.seller_id

            LEFT JOIN seller_order_counts soc
                ON s.seller_id = soc.seller_id

            LEFT JOIN seller_reviews sv
                ON s.seller_id = sv.seller_id

            LEFT JOIN seller_delivery sd
                ON s.seller_id = sd.seller_id

            WHERE 1 = 1
        """

        # ---------------------------------------------------------
        # Optional state filter
        # ---------------------------------------------------------

        if state:

            query += """
                AND UPPER(s.seller_state) = UPPER(?)
            """

            params.append(state)

        # ---------------------------------------------------------
        # Sort by first requested metric
        # ---------------------------------------------------------

        sort_metric = requested_metrics[0]

        query += f"""
            ORDER BY {sort_metric} {sort.upper()}
        """

        # ---------------------------------------------------------
        # Limit
        # ---------------------------------------------------------

        if limit is not None:
            query += """
                LIMIT ?
            """
            params.append(limit)

        # ---------------------------------------------------------
        # Execute
        # ---------------------------------------------------------

        try:

            with get_connection() as connection:

                rows = connection.execute(
                    query,
                    params,
                ).fetchall()

        except Exception as exc:

            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": str(exc),
                },
            }

        if not rows:

            return {
                "success": False,
                "error": {
                    "code": "NO_RESULTS",
                    "message": (
                        "No seller data was found "
                        "for the specified filters."
                    ),
                },
            }

        # ---------------------------------------------------------
        # Format result
        # ---------------------------------------------------------

        data = []

        for row in rows:

            item = {
                "seller_id": row["seller_id"],
                "seller_city": row["seller_city"],
                "seller_state": row["seller_state"],
            }

            for requested_metric in requested_metrics:
                item[requested_metric] = row[requested_metric]

            data.append(item)

        # ---------------------------------------------------------
        # Return
        # ---------------------------------------------------------

        return {
            "success": True,
            "data": data,
            "metadata": {
                "start_date": start_date,
                "end_date": end_date,
                "metrics": requested_metrics,
                "state": state,
                "limit": limit,
                "sort": sort,
                "row_count": len(data),
            },
        }