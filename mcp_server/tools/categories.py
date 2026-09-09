from fastmcp import FastMCP
from mcp_server.database import get_connection


def register_category_tools(mcp: FastMCP):

    @mcp.tool()
    def get_category_performance(
        start_date: str,
        end_date: str,
        metric: str,
        category: str | None = None,
        categories: list[str] | None = None,
        limit: int = 10,
        sort: str = "desc",
    ) -> dict:
        """
        Analyze product category performance.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

            metric:
                revenue
                order_count
                average_review_score
                freight_value

            category:
                Optional single English category name.

            categories:
                Optional list of English category names.
                Useful when comparing a specific set of categories.

            limit:
                Maximum number of categories to return.

            sort:
                Sort direction: asc or desc.
        """

        # ---------------------------------------------------------
        # Validation
        # ---------------------------------------------------------

        allowed_metrics = {
            "revenue",
            "order_count",
            "average_review_score",
            "freight_value",
        }

        if metric not in allowed_metrics:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": (
                        f"Invalid metric: '{metric}'. "
                        f"Allowed values: {sorted(allowed_metrics)}"
                    ),
                },
            }

        if sort not in {"asc", "desc"}:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "sort must be either 'asc' or 'desc'.",
                },
            }

        if limit <= 0:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "limit must be greater than 0.",
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

        if category and categories:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": (
                        "Provide either 'category' or 'categories', "
                        "not both."
                    ),
                },
            }

        # ---------------------------------------------------------
        # Build category filter
        # ---------------------------------------------------------

        category_filter = ""
        category_params = []

        if category:

            category_filter = """
                AND LOWER(category) = LOWER(?)
            """

            category_params.append(category)

        elif categories:

            if not categories:
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_PARAMETER",
                        "message": (
                            "categories must contain at least one category."
                        ),
                    },
                }

            placeholders = ", ".join(
                ["?" for _ in categories]
            )

            category_filter = f"""
                AND LOWER(category) IN (
                    {placeholders}
                )
            """

            category_params.extend(
                [item.lower() for item in categories]
            )

        # ---------------------------------------------------------
        # Revenue
        # ---------------------------------------------------------

        if metric == "revenue":

            query = f"""
                SELECT
                    COALESCE(
                        ct.product_category_name_english,
                        'unknown'
                    ) AS category,

                    ROUND(
                        SUM(oi.price),
                        2
                    ) AS metric_value

                FROM orders o

                JOIN order_items oi
                    ON o.order_id = oi.order_id

                JOIN products pr
                    ON oi.product_id = pr.product_id

                LEFT JOIN category_translation ct
                    ON pr.product_category_name =
                       ct.product_category_name

                WHERE
                    date(o.order_purchase_timestamp)
                    BETWEEN date(?) AND date(?)

                GROUP BY category

                HAVING
                    1 = 1

                    {category_filter}

                ORDER BY metric_value
                {"DESC" if sort == "desc" else "ASC"}

                LIMIT ?
            """

            params = (
                [start_date, end_date]
                + category_params
                + [limit]
            )

        # ---------------------------------------------------------
        # Order count
        # ---------------------------------------------------------

        elif metric == "order_count":

            query = f"""
                SELECT
                    COALESCE(
                        ct.product_category_name_english,
                        'unknown'
                    ) AS category,

                    COUNT(DISTINCT o.order_id)
                        AS metric_value

                FROM orders o

                JOIN order_items oi
                    ON o.order_id = oi.order_id

                JOIN products pr
                    ON oi.product_id = pr.product_id

                LEFT JOIN category_translation ct
                    ON pr.product_category_name =
                       ct.product_category_name

                WHERE
                    date(o.order_purchase_timestamp)
                    BETWEEN date(?) AND date(?)

                GROUP BY category

                HAVING
                    1 = 1

                    {category_filter}

                ORDER BY metric_value
                {"DESC" if sort == "desc" else "ASC"}

                LIMIT ?
            """

            params = (
                [start_date, end_date]
                + category_params
                + [limit]
            )

        # ---------------------------------------------------------
        # Freight
        # ---------------------------------------------------------

        elif metric == "freight_value":

            query = f"""
                SELECT
                    COALESCE(
                        ct.product_category_name_english,
                        'unknown'
                    ) AS category,

                    ROUND(
                        SUM(oi.freight_value),
                        2
                    ) AS metric_value

                FROM orders o

                JOIN order_items oi
                    ON o.order_id = oi.order_id

                JOIN products pr
                    ON oi.product_id = pr.product_id

                LEFT JOIN category_translation ct
                    ON pr.product_category_name =
                       ct.product_category_name

                WHERE
                    date(o.order_purchase_timestamp)
                    BETWEEN date(?) AND date(?)

                GROUP BY category

                HAVING
                    1 = 1

                    {category_filter}

                ORDER BY metric_value
                {"DESC" if sort == "desc" else "ASC"}

                LIMIT ?
            """

            params = (
                [start_date, end_date]
                + category_params
                + [limit]
            )

        # ---------------------------------------------------------
        # Average review score
        # ---------------------------------------------------------

        else:

            query = f"""
                WITH order_categories AS (

                    SELECT DISTINCT
                        o.order_id,

                        COALESCE(
                            ct.product_category_name_english,
                            'unknown'
                        ) AS category

                    FROM orders o

                    JOIN order_items oi
                        ON o.order_id = oi.order_id

                    JOIN products pr
                        ON oi.product_id = pr.product_id

                    LEFT JOIN category_translation ct
                        ON pr.product_category_name =
                           ct.product_category_name

                    WHERE
                        date(o.order_purchase_timestamp)
                        BETWEEN date(?) AND date(?)
                ),

                review_scores AS (

                    SELECT
                        r.order_id,
                        AVG(r.review_score)
                            AS review_score

                    FROM order_reviews r

                    GROUP BY r.order_id
                )

                SELECT
                    oc.category,

                    ROUND(
                        AVG(rs.review_score),
                        2
                    ) AS metric_value

                FROM order_categories oc

                JOIN review_scores rs
                    ON oc.order_id = rs.order_id

                WHERE
                    1 = 1

                    {category_filter}

                GROUP BY oc.category

                ORDER BY metric_value
                {"DESC" if sort == "desc" else "ASC"}

                LIMIT ?
            """

            params = (
                [start_date, end_date]
                + category_params
                + [limit]
            )

        # ---------------------------------------------------------
        # Execute
        # ---------------------------------------------------------

        try:

            with get_connection() as connection:

                rows = connection.execute(
                    query,
                    params,
                ).fetchall()

                data = [
                    {
                        "category": row["category"],
                        metric: row["metric_value"],
                    }
                    for row in rows
                ]

        except Exception as exc:

            return {
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": str(exc),
                },
            }

        # ---------------------------------------------------------
        # Empty result
        # ---------------------------------------------------------

        if not data:

            return {
                "success": False,
                "error": {
                    "code": "NO_RESULTS",
                    "message": (
                        "No category data was found "
                        "for the specified filters."
                    ),
                },
            }

        # ---------------------------------------------------------
        # Return
        # ---------------------------------------------------------

        return {
            "success": True,
            "data": data,
            "metadata": {
                "row_count": len(data),
                "start_date": start_date,
                "end_date": end_date,
                "metric": metric,
                "category": category,
                "categories": categories,
                "limit": limit,
                "sort": sort,
            },
        }