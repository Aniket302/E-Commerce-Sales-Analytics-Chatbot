import os
import json
import asyncio

from dotenv import load_dotenv
from groq import Groq
from fastmcp import Client

from agent.interface import ILLMAgent
from agent.tool_definitions import TOOL_DEFINITIONS
from agent.chart_rules import (
    choose_chart_type,
    choose_multi_tool_chart,
)
from agent.response_builder import build_deterministic_answer
from mcp_server.server import mcp

from agent.orchestration import (
    identify_analysis_type,
    build_required_tool_calls,
    build_dependent_tool_calls,
    build_multi_tool_analysis,
)

load_dotenv()


class LLMAgent(ILLMAgent):

    def __init__(self):

        self.model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-120b",
        )

        self.timeout = float(
            os.getenv("LLM_TIMEOUT", "30")
        )

        self.mcp_timeout = float(
            os.getenv("MCP_TIMEOUT", "30")
        )

        self.client = Groq(
            api_key=os.getenv("GROQ_API_KEY"),
            timeout=self.timeout,
        )

    # ==========================================================
    # Insight cleanup
    # ==========================================================

    @staticmethod
    def clean_insight(text: str) -> str:
        """
        Clean the LLM response so that only a short insight remains.

        Requirements:
        - Maximum 3 sentences
        - Remove unnecessary headings
        - Remove bullets
        - Remove additional sections
        """

        if not text:
            return "No insight available."

        text = text.strip()

        # ------------------------------------------------------
        # Remove common Insight headings
        # ------------------------------------------------------

        headings = [
            "**Insight:**",
            "**Insight**",
            "Insight:",
            "Insight",
        ]

        for heading in headings:

            if text.lower().startswith(
                heading.lower()
            ):

                text = text[
                    len(heading):
                ].strip()

        # ------------------------------------------------------
        # Remove accidental extra sections
        # ------------------------------------------------------

        section_markers = [
            "\n**Summary:**",
            "\n**Analysis:**",
            "\n**Findings:**",
            "\n**Key Takeaways:**",
            "\n**Conclusion:**",

            "\nSummary:",
            "\nAnalysis:",
            "\nFindings:",
            "\nKey Takeaways:",
            "\nConclusion:",
        ]

        text_lower = text.lower()

        cut_position = None

        for marker in section_markers:

            position = text_lower.find(
                marker.lower()
            )

            if position != -1:

                if (
                    cut_position is None
                    or position < cut_position
                ):
                    cut_position = position

        if cut_position is not None:
            text = text[:cut_position].strip()

        # ------------------------------------------------------
        # Remove bullet formatting
        # ------------------------------------------------------

        lines = []

        for line in text.splitlines():

            line = line.strip()

            if not line:
                continue

            if line.startswith("- "):
                line = line[2:].strip()

            elif line.startswith("* "):
                line = line[2:].strip()

            lines.append(line)

        text = " ".join(lines)

        # ------------------------------------------------------
        # Maximum 3 sentences
        # ------------------------------------------------------

        sentences = []

        current = ""

        for char in text:

            current += char

            if char in ".!?":

                sentences.append(
                    current.strip()
                )

                current = ""

                if len(sentences) >= 3:
                    break

        # Handle text without punctuation
        if (
            current.strip()
            and len(sentences) < 3
        ):
            sentences.append(
                current.strip()
            )

        text = " ".join(sentences)

        return text.strip()

    # ==========================================================
    # Execute one MCP tool call
    # ==========================================================

    async def _execute_tool_call(
        self,
        mcp_client,
        tool_name: str,
        tool_args: dict,
    ) -> dict:

        try:

            # --------------------------------------------------
            # Remove null optional arguments
            # --------------------------------------------------

            tool_args = {
                key: value
                for key, value in tool_args.items()
                if value is not None
            }

            # --------------------------------------------------
            # Execute with timeout
            # --------------------------------------------------

            result = await asyncio.wait_for(
                mcp_client.call_tool(
                    tool_name,
                    tool_args,
                ),
                timeout=self.mcp_timeout,
            )

            # --------------------------------------------------
            # MCP error
            # --------------------------------------------------

            if result.is_error:

                return {
                    "success": False,
                    "tool": tool_name,
                    "arguments": tool_args,
                    "data": [],
                    "error": (
                        "MCP tool returned an error."
                    ),
                }

            # --------------------------------------------------
            # Extract structured result
            # --------------------------------------------------

            tool_data = result.data

            # --------------------------------------------------
            # Defensive handling if returned as JSON string
            # --------------------------------------------------

            if isinstance(
                tool_data,
                str,
            ):

                try:

                    tool_data = json.loads(
                        tool_data
                    )

                except json.JSONDecodeError:

                    return {
                        "success": False,
                        "tool": tool_name,
                        "arguments": tool_args,
                        "data": [],
                        "error": (
                            "Tool returned invalid JSON."
                        ),
                    }

            return {
                "success": True,
                "tool": tool_name,
                "arguments": tool_args,
                "data": tool_data,
            }

        except asyncio.TimeoutError:

            return {
                "success": False,
                "tool": tool_name,
                "arguments": tool_args,
                "data": [],
                "error": (
                    f"MCP tool timed out after "
                    f"{self.mcp_timeout} seconds."
                ),
            }

        except Exception as exc:

            return {
                "success": False,
                "tool": tool_name,
                "arguments": tool_args,
                "data": [],
                "error": str(exc),
            }

    # ==========================================================
    # Ask LLM
    # ==========================================================

    async def ask(self, user_query: str) -> dict:

        # --------------------------------------------------
        # 1. Identify whether this is a known multi-tool query
        # --------------------------------------------------

        analysis_type = identify_analysis_type(user_query)

        print("\nAnalysis type:")
        print(analysis_type)

        # --------------------------------------------------
        # 2. System prompt for the LLM
        # --------------------------------------------------

        system_prompt = (
            "You are an analytics query router for an e-commerce dataset.\n\n"

            "IMPORTANT DATE RULES:\n"
            "- If the user does not specify a date or time period, ALWAYS use the full dataset.\n"
            "- Full dataset start_date is 2016-09-04.\n"
            "- Full dataset end_date is 2018-10-17.\n"
            "- NEVER ask the user which date range they want.\n"
            "- Only use a different date range when the user explicitly specifies one.\n\n"

            "DELIVERY PERFORMANCE RULES:\n"
            "- 'delivery performance' means delivery reliability.\n"
            "- 'worst delivery performance' means the LOWEST on_time_rate.\n"
            "- 'best delivery performance' means the HIGHEST on_time_rate.\n"
            "- When the user asks which states have the worst delivery performance, "
            "use group_by='customer_state'.\n"
            "- When the user asks which states have the best delivery performance, "
            "use group_by='customer_state'.\n"
            "- For 'worst' rankings, use sort='asc'.\n"
            "- For 'best' rankings, use sort='desc'.\n"
            "- For state rankings, use limit=10 unless the user explicitly requests "
            "a different number.\n\n"

            "RANKING RULES:\n"
            "- 'top N' means limit=N and sort='desc'.\n"
            "- 'worst N' means limit=N and sort='asc'.\n"
            "- If no N is specified for a ranking question, use limit=10.\n\n"

            "PAYMENT SHARE RULES:\n"
            "- 'share of payments' means payment value percentage by payment type.\n"
            "- For payment share questions, use get_payment_breakdown.\n"
            "- Use metric='payment_value'.\n"
            "- Use group_by='payment_type'.\n"
            "- 'credit card' maps to payment_type='credit_card'.\n"
            "- 'boleto' maps to payment_type='boleto'.\n"
            "- Payment share questions should be visualized as a part-to-whole chart.\n\n"

            "REVIEW RULES:\n"
            "- 'review score distribution' means metric='score_distribution'.\n"
            "- If the user specifies a product category, pass it as the category parameter.\n"
            "- Product categories supplied by users should be interpreted using the English category translation.\n"
            "- Example: 'review score distribution for electronics' means category='electronics'.\n\n"

            "MULTI-TOOL ANALYSIS RULES:\n"
            "- Some questions require combining results from multiple analytics tools.\n"
            "- Never invent values that are not present in tool results.\n"
            "- When comparing two metrics, make sure they refer to the same entities or time periods.\n\n"

            "CATEGORY + REVIEW:\n"
            "- For category volume/order comparisons with review scores, first obtain the requested "
            "categories by order volume.\n"
            "- Then obtain review scores for those exact categories.\n"
            "- Do not compare unrelated category sets.\n\n"

            "MONTHLY ORDERS + REVIEW:\n"
            "- For monthly order counts and review scores, use the same date range.\n"
            "- Group both datasets by month.\n\n"

            "SELLER DELIVERY + REVIEW:\n"
            "- For seller delivery speed and review scores, use the same sellers.\n"
            "- Delivery speed should use average_delivery_days.\n"
            "- Review performance should use average_review_score.\n\n"

            "STATE DELIVERY + REVIEW:\n"
            "- For state delivery delay and review scores, use customer_state.\n"
            "- Both datasets must refer to the same customer states.\n\n"

            "Use the available analytics tools to answer the user's question.\n"
            "Do not invent dataset values."
        )

        # --------------------------------------------------
        # 3. Initial LLM tool selection
        # --------------------------------------------------

        response = await asyncio.wait_for(
            asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_query,
                    },
                ],
                tools=[
                    {
                        "type": "function",
                        "function": tool,
                    }
                    for tool in TOOL_DEFINITIONS
                ],
                tool_choice="auto",
            ),
            timeout=self.timeout,
        )

        message = response.choices[0].message

        # --------------------------------------------------
        # 4. No tool selected
        # --------------------------------------------------

        if not message.tool_calls:

            # For a recognized multi-tool query, the LLM may occasionally
            # fail to initiate the tool call. In that case we use our
            # deterministic planner as a guardrail.

            if analysis_type:

                required_calls = build_required_tool_calls(
                    analysis_type,
                    user_query,
                )

                if required_calls:

                    print("\nLLM did not select a tool.")
                    print("Using deterministic multi-tool planner.")

                    tool_results = []

                    async with Client(mcp) as mcp_client:

                        for call in required_calls:

                            result = await self._execute_tool_call(
                                mcp_client,
                                call["tool"],
                                call["arguments"],
                            )

                            tool_results.append(result)

                        # --------------------------------------------------
                        # Execute dependent tools
                        # --------------------------------------------------

                        dependent_calls = build_dependent_tool_calls(
                            analysis_type,
                            tool_results,
                        )

                        for call in dependent_calls:

                            already_exists = any(
                                existing["tool"] == call["tool"]
                                and existing["arguments"] == call["arguments"]
                                for existing in tool_results
                            )

                            if already_exists:
                                continue

                            result = await self._execute_tool_call(
                                mcp_client,
                                call["tool"],
                                call["arguments"],
                            )

                            tool_results.append(result)

                    return await self._build_final_response(
                        user_query,
                        system_prompt,
                        analysis_type,
                        tool_results,
                    )

            return {
                "success": True,
                "answer": message.content,
                "tool": None,
                "arguments": None,
                "data": None,
                "chart": None,
            }

        # --------------------------------------------------
        # 5. Execute ALL LLM-selected tool calls
        # --------------------------------------------------

        tool_results = []

        async with Client(mcp) as mcp_client:

            for tool_call in message.tool_calls:

                tool_name = tool_call.function.name

                try:
                    tool_args = json.loads(
                        tool_call.function.arguments or "{}"
                    )
                except json.JSONDecodeError:

                    tool_args = {}

                print("\nSelected MCP tool:")
                print(tool_name)

                print("\nTool arguments:")
                print(tool_args)

                result = await self._execute_tool_call(
                    mcp_client,
                    tool_name,
                    tool_args,
                )

                tool_results.append(result)

            # --------------------------------------------------
            # 6. Execute dependent tool calls
            # --------------------------------------------------

            if analysis_type:

                dependent_calls = build_dependent_tool_calls(
                    analysis_type,
                    tool_results,
                )

                for call in dependent_calls:

                    already_exists = any(
                        existing["tool"] == call["tool"]
                        and existing["arguments"] == call["arguments"]
                        for existing in tool_results
                    )

                    if already_exists:
                        continue

                    print("\nDependent MCP tool:")
                    print(call["tool"])

                    print("\nDependent tool arguments:")
                    print(call["arguments"])

                    result = await self._execute_tool_call(
                        mcp_client,
                        call["tool"],
                        call["arguments"],
                    )

                    tool_results.append(result)

        # --------------------------------------------------
        # 7. Check for tool failures
        # --------------------------------------------------

        successful_results = [
            result
            for result in tool_results
            if result.get("success", False)
        ]

        failed_results = [
            result
            for result in tool_results
            if not result.get("success", False)
        ]

        if not successful_results:

            failed_tools = [
                result.get("tool", "unknown")
                for result in failed_results
            ]

            return {
                "success": False,
                "answer": (
                    "The analytics tools failed while processing this request. "
                    f"Failed tools: {', '.join(failed_tools)}"
                ),
                "tool": None,
                "arguments": None,
                "data": None,
                "chart": None,
            }

        # --------------------------------------------------
        # 8. Build multi-tool analysis
        # --------------------------------------------------

        multi_tool_analysis = None

        if analysis_type:

            multi_tool_analysis = build_multi_tool_analysis(
                analysis_type,
                tool_results,
            )

        # --------------------------------------------------
        # 9. Build deterministic facts
        # --------------------------------------------------

        deterministic_facts = []

        for result in successful_results:

            facts = build_deterministic_answer(
                result["tool"],
                result["arguments"],
                result["data"],
            )

            deterministic_facts.append(
                {
                    "tool": result["tool"],
                    "facts": facts,
                }
            )

        # --------------------------------------------------
        # 10. Build authoritative context
        # --------------------------------------------------

        if multi_tool_analysis and multi_tool_analysis.get("success"):

            authoritative_data = multi_tool_analysis.get(
                "data",
                [],
            )

            analysis_context = {
                "analysis_type": analysis_type,
                "combined_analysis": multi_tool_analysis,
                "deterministic_facts": deterministic_facts,
                "tool_results": tool_results,
            }

        else:

            # Single-tool query

            authoritative_data = successful_results[0].get(
                "data",
                {},
            )

            analysis_context = {
                "deterministic_facts": deterministic_facts,
                "tool_results": tool_results,
            }

        # --------------------------------------------------
        # 11. Ask LLM to explain authoritative results
        # --------------------------------------------------

        final_messages = [
            {
                "role": "system",
                "content": (
                    system_prompt
                    + "\n\n"
                    + "IMPORTANT:\n"
                    + "The following analytics results are authoritative.\n"
                    + "Answer using ONLY the supplied results.\n"
                    + "Do not invent, estimate, or hallucinate dataset values.\n"
                    + "If a value is missing, say that it is unavailable.\n"
                    + "Clearly explain the main finding and relevant comparisons."
                ),
            },
            {
                "role": "user",
                "content": user_query,
            },
            {
                "role": "user",
                "content": (
                    "AUTHORITATIVE ANALYTICS RESULT:\n"
                    + json.dumps(
                        analysis_context,
                        ensure_ascii=False,
                        default=str,
                    )
                ),
            },
        ]

        final_response = await asyncio.wait_for(
            asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=final_messages,
            ),
            timeout=self.timeout,
        )

        answer = final_response.choices[0].message.content

        # --------------------------------------------------
        # 12. Determine chart
        # --------------------------------------------------

        chart = None

        if (
            multi_tool_analysis
            and multi_tool_analysis.get("success")
        ):

            chart = choose_multi_tool_chart(
                analysis_type,
                multi_tool_analysis.get("data", []),
            )

        else:

            # Normal single-tool query

            first_result = successful_results[0]

            chart = choose_chart_type(
                first_result["tool"],
                first_result["arguments"],
                first_result["data"].get("data", []),
            )

        # --------------------------------------------------
        # 13. Add chart explanation
        # --------------------------------------------------

        chart_label = None
        justification = None

        if chart:

            chart_type = chart.get(
                "type",
                "unknown",
            )

            type_labels = {
                "bar": "Bar chart",
                "line": "Line chart",
                "dual_line": "Dual-axis line chart",
                "pie": "Pie chart",
                "donut": "Donut chart",
                "scatter": "Scatter plot",
            }

            chart_label = type_labels.get(
                chart_type,
                chart_type.replace("_", " ").title(),
            )

            justification = chart.get(
                "justification",
                "This chart type best matches the structure of the requested data.",
            )

            answer = (
                f"{answer}\n\n"
                f"**Chart:** {chart_label}\n\n"
                f"**Chart Justification:** {justification}"
            )

        # --------------------------------------------------
        # 14. Return structured result
        # --------------------------------------------------

        if analysis_type and multi_tool_analysis:

            return {
                "success": True,
                "answer": answer,
                "tool": "multi_tool",
                "analysis_type": analysis_type,
                "arguments": [
                    {
                        "tool": result["tool"],
                        "arguments": result["arguments"],
                    }
                    for result in tool_results
                ],
                "data": authoritative_data,
                "tool_results": tool_results,
                "analysis": multi_tool_analysis,
                "chart": chart,
                "chart_type": chart_label,
                "chart_justification": justification,
            }

        # Normal single-tool response

        first_result = successful_results[0]

        return {
            "success": True,
            "answer": answer,
            "tool": first_result["tool"],
            "arguments": first_result["arguments"],
            "data": first_result["data"],
            "tool_results": tool_results,
            "chart": chart,
            "chart_type": chart_label,
            "chart_justification": justification,
        }