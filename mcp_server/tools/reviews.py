from fastmcp import FastMCP
from mcp_server.database import get_connection


def register_review_tools(mcp: FastMCP):

    @mcp.tool
    def get_review_analysis(
        start_date: str,
        end_date: str,
        metric: str,
        category: str | None = None,
        group_by: str | None = None,
        limit: int = 10,
        sort: str = "desc",
    ) -> dict:
        """
        Analyze customer reviews over a specified date range.

        Supported metrics:
        - score_distribution
        - average_review_score
        - review_count
        - average_response_time_hours

        Supported group_by values:
        - month
        - customer_state
        - category
        - None

        category:
        - Optional English product category filter.
        """

        # -----------------------------
        # Validate inputs
        # -----------------------------

        valid_metrics = {
            "score_distribution",
            "average_review_score",
            "review_count",
            "average_response_time_hours",
        }

        valid_group_by = {
            None,
            "month",
            "customer_state",
            "category",
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

        if group_by not in valid_group_by:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_GROUP_BY",
                    "message": (
                        f"Unsupported group_by '{group_by}'. "
                        f"Supported values: month, customer_state, category, or None."
                    ),
                },
            }

        # Score distribution is already grouped by review score.
        # Do not allow another grouping dimension at the same time.
        if metric == "score_distribution" and group_by is not None:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_GROUPING",
                    "message": (
                        "score_distribution cannot be combined with group_by. "
                        "Use group_by=None."
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
        # Optional category filter
        # -----------------------------

        category_filter = ""
        category_params = []

        if category:
            category_filter = """
                AND r.order_id IN (
                    SELECT DISTINCT oi.order_id
                    FROM order_items oi
                    JOIN products p
                        ON oi.product_id = p.product_id
                    LEFT JOIN category_translation ct
                        ON p.product_category_name = ct.product_category_name
                    WHERE LOWER(
                        COALESCE(
                            ct.product_category_name_english,
                            p.product_category_name
                        )
                    ) = LOWER(?)
                )
            """

            category_params.append(category)

        # -----------------------------
        # Determine grouping expression
        # -----------------------------

        group_expression = None
        group_name = None

        if group_by == "month":
            group_expression = "strftime('%Y-%m', r.review_creation_date)"
            group_name = "month"

        elif group_by == "customer_state":
            group_expression = "c.customer_state"
            group_name = "customer_state"

        elif group_by == "category":
            group_expression = """
                COALESCE(
                    ct.product_category_name_english,
                    p.product_category_name
                )
            """
            group_name = "category"

        # -----------------------------
        # Build query
        # -----------------------------

        try:

            connection = get_connection()

            # =========================================
            # SCORE DISTRIBUTION
            # =========================================

            if metric == "score_distribution":

                query = f"""
                    SELECT
                        r.review_score,
                        COUNT(*) AS review_count

                    FROM order_reviews r

                    WHERE
                        DATE(r.review_creation_date)
                        BETWEEN DATE(?) AND DATE(?)

                        {category_filter}

                    GROUP BY r.review_score

                    ORDER BY r.review_score ASC
                """

                params = [start_date, end_date] + category_params

            # =========================================
            # GROUPED METRICS
            # =========================================

            elif group_by is not None:

                # -------------------------------------
                # Group by category
                # -------------------------------------

                if group_by == "category":

                    query = f"""
                        SELECT
                            {
                                group_expression
                            } AS category,
                            AVG(r.review_score) AS average_review_score,
                            COUNT(*) AS review_count

                        FROM order_reviews r

                        JOIN order_items oi
                            ON r.order_id = oi.order_id

                        JOIN products p
                            ON oi.product_id = p.product_id

                        LEFT JOIN category_translation ct
                            ON p.product_category_name =
                               ct.product_category_name

                        WHERE
                            DATE(r.review_creation_date)
                            BETWEEN DATE(?) AND DATE(?)

                            {category_filter}

                        GROUP BY
                            {group_expression}

                        ORDER BY
                            average_review_score
                            {sort.upper()}

                        LIMIT ?
                    """

                    params = (
                        [start_date, end_date]
                        + category_params
                        + [limit]
                    )

                # -------------------------------------
                # Group by customer state
                # -------------------------------------

                elif group_by == "customer_state":

                    query = f"""
                        SELECT
                            c.customer_state AS customer_state,
                            AVG(r.review_score) AS average_review_score,
                            COUNT(*) AS review_count

                        FROM order_reviews r

                        JOIN orders o
                            ON r.order_id = o.order_id

                        JOIN customers c
                            ON o.customer_id = c.customer_id

                        WHERE
                            DATE(r.review_creation_date)
                            BETWEEN DATE(?) AND DATE(?)

                            {category_filter}

                        GROUP BY
                            c.customer_state

                        ORDER BY
                            average_review_score
                            {sort.upper()}

                        LIMIT ?
                    """

                    params = (
                        [start_date, end_date]
                        + category_params
                        + [limit]
                    )

                # -------------------------------------
                # Group by month
                # -------------------------------------

                else:

                    query = f"""
                        SELECT
                            strftime(
                                '%Y-%m',
                                r.review_creation_date
                            ) AS month,

                            AVG(r.review_score)
                                AS average_review_score,

                            COUNT(*) AS review_count

                        FROM order_reviews r

                        WHERE
                            DATE(r.review_creation_date)
                            BETWEEN DATE(?) AND DATE(?)

                            {category_filter}

                        GROUP BY
                            strftime(
                                '%Y-%m',
                                r.review_creation_date
                            )

                        ORDER BY
                            month ASC
                    """

                    params = (
                        [start_date, end_date]
                        + category_params
                    )

            # =========================================
            # UNGROUPED METRICS
            # =========================================

            elif metric == "average_review_score":

                query = f"""
                    SELECT
                        AVG(r.review_score)
                            AS average_review_score

                    FROM order_reviews r

                    WHERE
                        DATE(r.review_creation_date)
                        BETWEEN DATE(?) AND DATE(?)

                        {category_filter}
                """

                params = (
                    [start_date, end_date]
                    + category_params
                )

            elif metric == "review_count":

                query = f"""
                    SELECT
                        COUNT(*) AS review_count

                    FROM order_reviews r

                    WHERE
                        DATE(r.review_creation_date)
                        BETWEEN DATE(?) AND DATE(?)

                        {category_filter}
                """

                params = (
                    [start_date, end_date]
                    + category_params
                )

            else:

                query = f"""
                    SELECT
                        AVG(
                            (
                                julianday(r.review_answer_timestamp)
                                -
                                julianday(r.review_creation_date)
                            ) * 24
                        ) AS average_response_time_hours

                    FROM order_reviews r

                    WHERE
                        DATE(r.review_creation_date)
                        BETWEEN DATE(?) AND DATE(?)

                        AND r.review_answer_timestamp IS NOT NULL
                        AND r.review_creation_date IS NOT NULL

                        {category_filter}
                """

                params = (
                    [start_date, end_date]
                    + category_params
                )

            # -----------------------------
            # Execute query
            # -----------------------------

            rows = connection.execute(
                query,
                params
            ).fetchall()

            connection.close()

            # -----------------------------
            # Format result
            # -----------------------------

            data = []

            for row in rows:

                # Score distribution
                if metric == "score_distribution":

                    data.append({
                        "review_score": row["review_score"],
                        "review_count": row["review_count"],
                    })

                # Grouped results
                elif group_by == "month":

                    data.append({
                        "month": row["month"],
                        "average_review_score": row["average_review_score"],
                        "review_count": row["review_count"],
                    })

                elif group_by == "customer_state":

                    data.append({
                        "customer_state": row["customer_state"],
                        "average_review_score": row["average_review_score"],
                        "review_count": row["review_count"],
                    })

                elif group_by == "category":

                    data.append({
                        "category": row["category"],
                        "average_review_score": row["average_review_score"],
                        "review_count": row["review_count"],
                    })

                # Ungrouped average
                elif metric == "average_review_score":

                    data.append({
                        "average_review_score": (
                            row["average_review_score"]
                        ),
                    })

                # Ungrouped count
                elif metric == "review_count":

                    data.append({
                        "review_count": row["review_count"],
                    })

                # Response time
                else:

                    data.append({
                        "average_response_time_hours": (
                            row["average_response_time_hours"]
                        ),
                    })

            # -----------------------------
            # Return result
            # -----------------------------

            return {
                "success": True,
                "data": data,
                "metadata": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "metric": metric,
                    "category": category,
                    "group_by": group_by,
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