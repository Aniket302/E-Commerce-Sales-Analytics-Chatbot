import requests
import streamlit as st
from chart_renderer import render_chart
from datetime import datetime
from zoneinfo import ZoneInfo


import os

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000",
)


def load_dashboard():
    response = requests.get(
        f"{API_BASE_URL}/dashboard",
        timeout=30,
    )

    if response.status_code != 200:
        return []

    return response.json().get("charts", [])


def format_ist_timestamp(timestamp: str) -> str:
    dt = datetime.fromisoformat(timestamp)

    ist = dt.astimezone(
        ZoneInfo("Asia/Kolkata")
    )

    return ist.strftime(
        "%d %b %Y, %I:%M:%S %p IST"
    )

st.set_page_config(
    page_title="E-Commerce Analytics",
    page_icon="📊",
    layout="wide",
)


st.title("E-Commerce Sales Analytics")
st.caption("Ask questions about the Olist e-commerce dataset.")


query = st.text_input(
    "Ask an analytics question",
    placeholder="e.g. What was the monthly revenue in 2017?",
)


if st.button("Analyze", type="primary"):

    if not query.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Analyzing..."):

            response = requests.post(
                f"{API_BASE_URL}/ask",
                json={"query": query},
                timeout=60,
            )

        if response.status_code != 200:
            st.error(
                f"API request failed: {response.status_code}"
            )
        else:
            result = response.json()

            st.session_state["latest_result"] = result


if "latest_result" in st.session_state:

    result = st.session_state["latest_result"]

    st.divider()

    st.subheader("Answer")

    if result.get("answer"):
        st.write(result["answer"])

    if result.get("chart"):
        st.subheader("Chart")

        raw_data = result.get("data", [])

        if isinstance(raw_data, dict):
            rows = raw_data.get("data", [])
        else:
            rows = raw_data

        figure = render_chart(
            result["chart"],
            rows,
        )

        if figure:
            st.plotly_chart(
                figure,
                width="stretch",
            )

            if st.button("📌 Pin to Dashboard"):
                pin_response = requests.post(
                    f"{API_BASE_URL}/dashboard/pin",
                    json={
                        "query": query,
                        "result": result,
                    },
                    timeout=30,
                )

                if pin_response.status_code == 200:
                    st.success("Chart pinned to dashboard!")
                else:
                    st.error(
                        f"Unable to pin chart: "
                        f"{pin_response.text}"
                    )

        else:
            st.warning("Unable to render this chart.")

    if result.get("data"):
        st.subheader("Data")

        rows = result["data"].get("data", [])

        if rows:
            st.dataframe(
                rows,
                width="stretch",
            )

st.divider()

st.header("📌 Pinned Dashboard")

pinned_charts = load_dashboard()

if not pinned_charts:
    st.info(
        "No charts have been pinned yet. "
        "Analyze a question and pin the chart to see it here."
    )

else:
    for pinned_chart in pinned_charts:

        chart_id = pinned_chart["id"]
        query_text = pinned_chart["query"]

        st.subheader(query_text)

        chart_spec = pinned_chart["chart"]
        chart_data = pinned_chart["data"]

        rows = chart_data.get("data", [])

        figure = render_chart(
            chart_spec,
            rows,
        )

        if figure:
            st.plotly_chart(
                figure,
                width="stretch",
                key=f"pinned_chart_{chart_id}",
            )
        else:
            st.warning(
                "Unable to render this pinned chart."
            )

        col1, col2, col3 = st.columns([1, 1, 9])

        with col1:
            if st.button(
                "🔄 Refresh",
                key=f"refresh_{chart_id}",
            ):
                with st.spinner("Refreshing..."):

                    response = requests.post(
                        f"{API_BASE_URL}/dashboard/{chart_id}/refresh",
                        timeout=60,
                    )

                if response.status_code == 200:
                    refresh_result = response.json()

                    st.session_state[
                        f"refresh_result_{chart_id}"
                    ] = refresh_result

                    st.rerun()

                else:
                    st.error(
                        f"Refresh failed: {response.text}"
                    )


        with col2:
            if st.button(
                "🗑️ Unpin",
                key=f"unpin_{chart_id}",
            ):
                response = requests.delete(
                    f"{API_BASE_URL}/dashboard/{chart_id}",
                    timeout=30,
                )

                if response.status_code == 200:
                    st.session_state.pop(
                        f"refresh_result_{chart_id}",
                        None,
                    )

                    st.success("Chart unpinned.")
                    st.rerun()

                else:
                    st.error(
                        f"Unable to unpin chart: {response.text}"
                    )


        with col3:
            st.caption(
                f"Last refreshed: "
                f"{format_ist_timestamp(pinned_chart['last_refreshed_at'])}"
            )

        refresh_result = st.session_state.get(
            f"refresh_result_{chart_id}"
        )

        if refresh_result:

            change_detection = refresh_result.get(
                "change_detection",
                {},
            )

            if change_detection.get("significant"):

                st.warning(
                    "⚠️ Significant change detected!"
                )

                for change in change_detection.get(
                    "changes",
                    [],
                ):
                    st.write(
                        f"**{change['field']}** for "
                        f"**{change['key']}** changed by "
                        f"**{change['percentage_change']}%** "
                        f"({change['old_value']} → "
                        f"{change['new_value']})."
                    )

            else:

                st.success(
                    "No significant changes detected."
                )

        st.divider()