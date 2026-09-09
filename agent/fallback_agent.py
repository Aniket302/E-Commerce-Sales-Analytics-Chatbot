from agent.interface import ILLMAgent
from agent.chart_rules import choose_chart_type
from fastmcp import Client
from mcp_server.server import mcp
from agent.response_builder import build_deterministic_answer


class FallbackAgent(ILLMAgent):

    async def ask(self, user_query: str) -> dict:

        query = user_query.lower()

        # --------------------------------------------------
        # 1. Determine date range
        # --------------------------------------------------

        start_date = None
        end_date = None

        if "2017" in query:
            start_date = "2017-01-01"
            end_date = "2017-12-31"

        elif "2018" in query:
            start_date = "2018-01-01"
            end_date = "2018-12-31"

        # --------------------------------------------------
        # 2. Detect limit
        # --------------------------------------------------

        limit = None

        if "top 10" in query:
            limit = 10

        elif "top 5" in query:
            limit = 5

        # --------------------------------------------------
        # 3. Detect sorting
        # --------------------------------------------------

        sort = "desc"

        if "worst" in query or "lowest" in query:
            sort = "asc"

        # --------------------------------------------------
        # 4. Detect tool
        # --------------------------------------------------

        tool_name = None
        tool_args = {}

        # --------------------------------------------------
        # ORDER TRENDS
        # --------------------------------------------------

        if "revenue" in query and (
            "monthly" in query
            or "month" in query
        ):
            tool_name = "get_order_trends"

            tool_args = {
                "start_date": start_date,
                "end_date": end_date,
                "metrics": ["revenue"],
                "group_by": "month",
            }

        # --------------------------------------------------
        # CATEGORY PERFORMANCE
        # --------------------------------------------------

        elif "categor" in query and "revenue" in query:

            tool_name = "get_category_performance"

            tool_args = {
                "start_date": start_date,
                "end_date": end_date,
                "metric": "revenue",
                "sort": sort,
            }

            if limit:
                tool_args["limit"] = limit

        # --------------------------------------------------
        # SELLER PERFORMANCE
        # --------------------------------------------------

        elif "seller" in query:

            tool_name = "get_seller_performance"

            metric = "revenue"

            if "review" in query or "rating" in query:
                metric = "average_review_score"

            elif "delivery" in query:
                metric = "average_delivery_days"

            tool_args = {
                "start_date": start_date,
                "end_date": end_date,
                "metric": metric,
                "sort": sort,
            }

            if limit:
                tool_args["limit"] = limit

            # São Paulo
            if (
                "são paulo" in query
                or "sao paulo" in query
                or "sp" in query
            ):
                tool_args["state"] = "SP"

        # --------------------------------------------------
        # REVIEW ANALYSIS
        # --------------------------------------------------

        elif "review" in query:

            tool_name = "get_review_analysis"

            if (
                "distribution" in query
                or "score" in query
                or "rating" in query
            ):
                metric = "score_distribution"

            elif "response" in query:
                metric = "average_response_time_hours"

            elif "count" in query:
                metric = "review_count"

            else:
                metric = "average_review_score"

            tool_args = {
                "start_date": start_date,
                "end_date": end_date,
                "metric": metric,
            }

        # --------------------------------------------------
        # PAYMENT BREAKDOWN
        # --------------------------------------------------

        elif "payment" in query:

            tool_name = "get_payment_breakdown"

            if (
                "installment" in query
                or "installments" in query
            ):
                metric = "average_installments"

            elif "count" in query:
                metric = "payment_count"

            else:
                metric = "payment_value"

            if "monthly" in query or "month" in query:
                group_by = "month"
            else:
                group_by = "payment_type"

            tool_args = {
                "start_date": start_date,
                "end_date": end_date,
                "metric": metric,
                "group_by": group_by,
                "sort": sort,
            }

            if limit:
                tool_args["limit"] = limit

        # --------------------------------------------------
        # DELIVERY PERFORMANCE
        # --------------------------------------------------

        elif "delivery" in query:

            tool_name = "get_delivery_performance"

            if "delay" in query:
                metric = "average_delay_days"

            elif "on time" in query:
                metric = "on_time_rate"

            elif "count" in query:
                metric = "order_count"

            else:
                metric = "average_delivery_days"

            if "seller state" in query:
                group_by = "seller_state"

            elif "customer state" in query:
                group_by = "customer_state"

            elif "route" in query:
                group_by = "route"

            else:
                group_by = "month"

            tool_args = {
                "start_date": start_date,
                "end_date": end_date,
                "metric": metric,
                "group_by": group_by,
                "sort": sort,
            }

            if limit:
                tool_args["limit"] = limit

        # --------------------------------------------------
        # Unsupported question
        # --------------------------------------------------

        if tool_name is None:

            return {
                "success": False,
                "answer": (
                    "I couldn't map your question to a supported "
                    "analytics operation."
                ),
                "tool": None,
                "arguments": None,
                "data": None,
                "chart": None,
            }

        # --------------------------------------------------
        # Remove missing dates
        # --------------------------------------------------

        if start_date is None:
            tool_args.pop("start_date", None)

        if end_date is None:
            tool_args.pop("end_date", None)

        # --------------------------------------------------
        # Execute MCP tool
        # --------------------------------------------------

        async with Client(mcp) as mcp_client:

            tool_result = await mcp_client.call_tool(
                tool_name,
                tool_args,
            )

        if tool_result.is_error:

            return {
                "success": False,
                "answer": "The analytics tool failed.",
                "tool": tool_name,
                "arguments": tool_args,
                "data": None,
                "chart": None,
            }

        tool_data = tool_result.data

        # --------------------------------------------------
        # Determine chart
        # --------------------------------------------------

        chart = choose_chart_type(
            tool_name,
            tool_args,
            tool_data.get("data", []),
        )

        deterministic_answer = build_deterministic_answer(
            tool_name,
            tool_args,
            tool_data,
        )

        return {
            "success": True,
            "answer": deterministic_answer,
            "tool": tool_name,
            "arguments": tool_args,
            "data": tool_data,
            "chart": chart,
        }