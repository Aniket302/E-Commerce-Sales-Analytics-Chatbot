import plotly.express as px


def render_chart(chart_spec: dict, rows: list[dict]):
    if not chart_spec or not rows:
        return None

    chart_type = chart_spec.get("type")

    if not chart_type:
        return None

    # ---------------------------------------------------------
    # LINE CHART
    # ---------------------------------------------------------

    if chart_type == "line":

        x_field = chart_spec.get("x")
        y_field = chart_spec.get("y")

        if not x_field or not y_field:
            return None

        # Convert a list of y-fields into a list.
        if isinstance(y_field, str):
            y_fields = [y_field]
        elif isinstance(y_field, list):
            y_fields = y_field
        else:
            y_fields = []

        if not y_fields:
            return None

        if len(y_fields) == 1:

            figure = px.line(
                rows,
                x=x_field,
                y=y_fields[0],
                markers=True,
            )

        else:

            figure = px.line(
                rows,
                x=x_field,
                y=y_fields,
                markers=True,
            )

    # ---------------------------------------------------------
    # DUAL-AXIS LINE CHART
    # ---------------------------------------------------------

    elif chart_type == "dual_line":

        x_field = chart_spec.get("x")
        y_fields = chart_spec.get("y")

        if not x_field or not y_fields:
            return None

        if not isinstance(y_fields, list) or len(y_fields) != 2:
            return None

        # Plotly Express does not create a true dual-axis chart
        # directly, so use graph_objects here.
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        figure = make_subplots(
            specs=[[{"secondary_y": True}]]
        )

        figure.add_trace(
            go.Scatter(
                x=[row.get(x_field) for row in rows],
                y=[row.get(y_fields[0]) for row in rows],
                mode="lines+markers",
                name=y_fields[0],
            ),
            secondary_y=False,
        )

        figure.add_trace(
            go.Scatter(
                x=[row.get(x_field) for row in rows],
                y=[row.get(y_fields[1]) for row in rows],
                mode="lines+markers",
                name=y_fields[1],
            ),
            secondary_y=True,
        )

        figure.update_yaxes(
            title_text=y_fields[0],
            secondary_y=False,
        )

        figure.update_yaxes(
            title_text=y_fields[1],
            secondary_y=True,
        )

    # ---------------------------------------------------------
    # BAR CHART
    # ---------------------------------------------------------

    elif chart_type == "bar":

        x_field = chart_spec.get("x")
        y_field = chart_spec.get("y")

        if not x_field or not y_field:
            return None

        if isinstance(y_field, list):
            if not y_field:
                return None
            y_value = y_field[0]
        else:
            y_value = y_field

        orientation = chart_spec.get(
            "orientation",
            "vertical",
        )

        if orientation == "horizontal":

            figure = px.bar(
                rows,
                x=y_value,
                y=x_field,
                orientation="h",
            )

        else:

            figure = px.bar(
                rows,
                x=x_field,
                y=y_value,
            )

    # ---------------------------------------------------------
    # PIE / DONUT
    # ---------------------------------------------------------

    elif chart_type in ("pie", "donut"):

        name_field = chart_spec.get("name")
        value_field = chart_spec.get("value")

        if not name_field or not value_field:
            return None

        # Verify that the requested fields actually exist.
        if name_field not in rows[0] or value_field not in rows[0]:
            return None

        figure = px.pie(
            rows,
            names=name_field,
            values=value_field,
            hole=0.45 if chart_type == "donut" else 0,
        )

    # ---------------------------------------------------------
    # SCATTER
    # ---------------------------------------------------------

    elif chart_type == "scatter":

        x_field = chart_spec.get("x")
        y_field = chart_spec.get("y")

        if not x_field or not y_field:
            return None

        if isinstance(y_field, list):
            if not y_field:
                return None
            y_value = y_field[0]
        else:
            y_value = y_field

        figure = px.scatter(
            rows,
            x=x_field,
            y=y_value,
        )

    # ---------------------------------------------------------
    # UNKNOWN CHART TYPE
    # ---------------------------------------------------------

    else:
        return None

    # ---------------------------------------------------------
    # COMMON FORMATTING
    # ---------------------------------------------------------

    title = chart_spec.get("title")

    if title:
        figure.update_layout(
            title=title,
        )

    figure.update_layout(
        margin=dict(
            l=40,
            r=20,
            t=60,
            b=40,
        ),
        height=450,
    )

    return figure