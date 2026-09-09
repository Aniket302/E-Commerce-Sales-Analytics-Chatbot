def choose_chart_type(
    tool_name: str,
    arguments: dict,
    data: list[dict]
) -> dict:

    # No data → no chart
    if not data:
        return {
            "type": None,
            "reason": "No data available for the requested query."
        }

    # ---------------------------------------------------------
    # Order trends
    # ---------------------------------------------------------

    if tool_name == "get_order_trends":

        metrics = arguments.get("metrics", [])
        group_by = arguments.get("group_by")

        # Single metric over time → line chart
        if len(metrics) == 1 and group_by in {
            "day",
            "week",
            "month",
            "year"
        }:
            return {
                "type": "line",
                "x": "period",
                "y": metrics[0],
                "justification": (
                    "A line chart is appropriate because the metric "
                    "is measured across an ordered time period."
                )
            }

        # Two metrics over same time axis → dual-axis line
        if len(metrics) == 2 and group_by in {
            "day",
            "week",
            "month",
            "year"
        }:
            return {
                "type": "dual_line",
                "x": "period",
                "y": metrics,
                "justification": (
                    "A dual-axis line chart is appropriate for comparing "
                    "two metrics across the same time axis."
                )
            }

    # ---------------------------------------------------------
    # Category performance
    # ---------------------------------------------------------

    if tool_name == "get_category_performance":

        limit = arguments.get("limit")

        # Ranked category result → horizontal bar
        if limit is not None:
            return {
                "type": "bar",
                "orientation": "horizontal",
                "x": "category",
                "y": arguments.get("metric"),
                "justification": (
                    "A horizontal bar chart is appropriate for comparing "
                    "ranked category performance."
                )
            }

        # Category comparison → vertical bar
        return {
            "type": "bar",
            "orientation": "vertical",
            "x": "category",
            "y": arguments.get("metric"),
            "justification": (
                "A vertical bar chart is appropriate for comparing "
                "performance across categories."
            )
        }

    # ---------------------------------------------------------
    # Seller performance
    # ---------------------------------------------------------

    if tool_name == "get_seller_performance":

        return {
            "type": "bar",
            "orientation": "horizontal",
            "x": "seller_id",
            "y": arguments.get("metric"),
            "justification": (
                "A horizontal bar chart is appropriate for comparing "
                "seller performance across ranked sellers."
            )
        }

    # ---------------------------------------------------------
    # Review analysis
    # ---------------------------------------------------------

    if tool_name == "get_review_analysis":

        metric = arguments.get("metric")

        # Review score distribution → horizontal bar
        if metric == "score_distribution":
            return {
                "type": "bar",
                "orientation": "horizontal",
                "x": "review_score",
                "y": "review_count",
                "justification": (
                    "A horizontal bar chart makes it easy to compare "
                    "review counts across the 1–5 star scores."
                )
            }

        # Other review metrics
        return {
            "type": "bar",
            "orientation": "vertical",
            "x": "metric",
            "y": "value",
            "justification": (
                "A bar chart is appropriate for comparing "
                "the returned review metric value."
            )
        }

    # ---------------------------------------------------------
    # Payment breakdown
    # ---------------------------------------------------------

    if tool_name == "get_payment_breakdown":

        group_by = arguments.get("group_by")
        metric = arguments.get("metric")

        # Payment share / composition
        if group_by == "payment_type" and metric == "payment_value":
            return {
                "type": "pie",
                "name": "payment_type",
                "value": "payment_value",
                "justification": (
                    "A pie chart is appropriate because payment types "
                    "represent parts of a single total payment value."
                )
            }

        # Payment breakdown over time
        if group_by == "month":
            return {
                "type": "line",
                "x": "month",
                "y": metric,
                "justification": (
                    "A line chart is appropriate because payment values "
                    "are being compared across an ordered time period."
                )
            }

        # Other categorical payment comparisons
        return {
            "type": "bar",
            "orientation": "horizontal",
            "x": group_by,
            "y": metric,
            "justification": (
                "A horizontal bar chart is appropriate for comparing "
                "payment metrics across payment categories."
            )
        }

    # ---------------------------------------------------------
    # Delivery performance
    # ---------------------------------------------------------

    if tool_name == "get_delivery_performance":

        group_by = arguments.get("group_by")
        metric = arguments.get("metric")

        # Monthly delivery trend
        if group_by == "month":
            return {
                "type": "line",
                "x": "month",
                "y": metric,
                "justification": (
                    "A line chart is appropriate because delivery "
                    "performance is tracked across an ordered time period."
                )
            }

        # Delivery performance by customer state
        if group_by == "customer_state":
            return {
                "type": "bar",
                "orientation": "horizontal",
                "x": "customer_state",
                "y": metric,
                "justification": (
                    "A horizontal bar chart clearly compares delivery "
                    "performance across customer states."
                )
            }

        # Delivery performance by seller state
        if group_by == "seller_state":
            return {
                "type": "bar",
                "orientation": "horizontal",
                "x": "seller_state",
                "y": metric,
                "justification": (
                    "A horizontal bar chart clearly compares delivery "
                    "performance across seller states."
                )
            }

        # Delivery performance by route
        if group_by == "route":
            return {
                "type": "bar",
                "orientation": "horizontal",
                "x": "route",
                "y": metric,
                "justification": (
                    "A horizontal bar chart is appropriate for comparing "
                    "delivery performance across routes."
                )
            }

    # ---------------------------------------------------------
    # Unknown / ambiguous
    # ---------------------------------------------------------

    return {
        "type": None,
        "reason": "Chart type could not be determined."
    }


def choose_multi_tool_chart(
    analysis_type: str,
    data: list[dict],
) -> dict:

    if not data:
        return {
            "type": None,
            "reason": "No data available for the requested comparison.",
        }

    # -----------------------------------------
    # Category volume vs review score
    # -----------------------------------------

    if analysis_type == "category_volume_review":

        return {
            "type": "bar",
            "orientation": "horizontal",
            "x": "category",
            "y": [
                "order_count",
                "average_review_score",
            ],
            "title": "Top Categories: Orders vs Review Score",
            "justification": (
                "A grouped horizontal bar chart makes it easy to "
                "compare the selected categories across two metrics."
            ),
        }

    # -----------------------------------------
    # Monthly orders vs review score
    # -----------------------------------------

    if analysis_type == "monthly_orders_review":

        return {
            "type": "dual_line",
            "x": "month",
            "y": [
                "order_count",
                "average_review_score",
            ],
            "title": "Monthly Orders vs Average Review Score",
            "justification": (
                "A dual-series line chart shows how order volume "
                "and review score change across the same monthly timeline."
            ),
        }

    # -----------------------------------------
    # Seller delivery vs review
    # -----------------------------------------

    if analysis_type == "seller_delivery_review":

        return {
            "type": "scatter",
            "x": "average_delivery_days",
            "y": "average_review_score",
            "title": "Seller Delivery Speed vs Review Score",
            "justification": (
                "A scatter plot is appropriate because each seller "
                "is one observation with two continuous variables."
            ),
        }

    # -----------------------------------------
    # State delivery delay vs review
    # -----------------------------------------

    if analysis_type == "state_delivery_review":

        return {
            "type": "bar",
            "orientation": "horizontal",
            "x": "customer_state",
            "y": [
                "average_delay_days",
                "average_review_score",
            ],
            "title": "Delivery Delay vs Review Score by State",
            "justification": (
                "A grouped horizontal bar chart allows comparison "
                "of delivery delay and review score across states."
            ),
        }

    return {
        "type": None,
        "reason": "No deterministic multi-tool chart rule matched.",
    }