def build_deterministic_answer(tool_name, tool_args, tool_data):
    data = tool_data.get("data", [])

    if not data:
        return "No data was found for the requested query."

    # --------------------------------------------------
    # Order trends
    # --------------------------------------------------

    if tool_name == "get_order_trends":

        metrics = tool_args.get("metrics", [])
        group_by = tool_args.get("group_by")

        if "revenue" in metrics:
            total = sum(
                float(row.get("revenue", 0))
                for row in data
            )

            if group_by == "month":
                return (
                    f"Revenue for the requested period was "
                    f"${total:,.2f} across {len(data)} months."
                )

            return (
                f"Revenue for the requested period was "
                f"${total:,.2f}."
            )

        if "order_count" in metrics:
            total = sum(
                int(row.get("order_count", 0))
                for row in data
            )

            return (
                f"There were {total:,} orders "
                f"across the requested period."
            )

    # --------------------------------------------------
    # Category performance
    # --------------------------------------------------

    if tool_name == "get_category_performance":

        metric = tool_args.get("metric")

        if metric == "revenue":

            total = sum(
                float(row.get("revenue", 0))
                for row in data
            )

            top_category = max(
                data,
                key=lambda row: float(row.get("revenue", 0))
            )

            category = top_category.get("category")
            revenue = float(top_category.get("revenue", 0))

            return (
                f"The returned categories generated "
                f"${total:,.2f} in revenue. "
                f"The highest-revenue category was "
                f"{category}, with ${revenue:,.2f}."
            )

        if metric == "average_review_score":

            top_category = max(
                data,
                key=lambda row: float(
                    row.get("average_review_score", 0)
                )
            )

            return (
                f"The highest-rated category in the returned "
                f"results was {top_category.get('category')}, "
                f"with an average review score of "
                f"{float(top_category.get('average_review_score', 0)):.2f}."
            )

    # --------------------------------------------------
    # Seller performance
    # --------------------------------------------------

    if tool_name == "get_seller_performance":

        metric = tool_args.get("metric")

        if metric == "revenue":

            top_seller = max(
                data,
                key=lambda row: float(row.get("revenue", 0))
            )

            return (
                f"The highest-revenue seller in the returned "
                f"results was {top_seller.get('seller_id')}, "
                f"with revenue of "
                f"${float(top_seller.get('revenue', 0)):,.2f}."
            )

        if metric == "average_review_score":

            top_seller = max(
                data,
                key=lambda row: float(
                    row.get("average_review_score", 0)
                )
            )

            return (
                f"The highest-rated seller in the returned "
                f"results was {top_seller.get('seller_id')}, "
                f"with an average review score of "
                f"{float(top_seller.get('average_review_score', 0)):.2f}."
            )

    # --------------------------------------------------
    # Review analysis
    # --------------------------------------------------

    if tool_name == "get_review_analysis":

        metric = tool_args.get("metric")

        if metric == "score_distribution":

            total_reviews = sum(
                int(row.get("review_count", 0))
                for row in data
            )

            positive_reviews = sum(
                int(row.get("review_count", 0))
                for row in data
                if int(row.get("review_score", 0)) >= 4
            )

            negative_reviews = sum(
                int(row.get("review_count", 0))
                for row in data
                if int(row.get("review_score", 0)) <= 2
            )

            positive_percentage = (
                positive_reviews / total_reviews * 100
                if total_reviews
                else 0
            )

            negative_percentage = (
                negative_reviews / total_reviews * 100
                if total_reviews
                else 0
            )

            return (
                f"There were {total_reviews:,} reviews. "
                f"{positive_reviews:,} reviews ({positive_percentage:.2f}%) "
                f"were rated 4 or 5 stars, while "
                f"{negative_reviews:,} ({negative_percentage:.2f}%) "
                f"were rated 1 or 2 stars."
            )

        if metric == "average_review_score":

            average = sum(
                float(row.get("average_review_score", 0))
                for row in data
            ) / len(data)

            return (
                f"The average review score was "
                f"{average:.2f}."
            )

    # --------------------------------------------------
    # Payment breakdown
    # --------------------------------------------------

        if tool_name == "get_payment_breakdown":

            metric = tool_args.get("metric")
            group_by = tool_args.get("group_by")

            if metric == "payment_value" and group_by == "payment_type":

                total = sum(
                    float(row.get("payment_value", 0))
                    for row in data
                )

                if total == 0:
                    return "No payment value was available for the requested period."

                shares = []

                for row in data:
                    payment_type = row.get("payment_type")
                    value = float(row.get("payment_value", 0))
                    share = (value / total) * 100

                    shares.append({
                        "payment_type": payment_type,
                        "payment_value": value,
                        "share_percentage": share,
                    })

                shares.sort(
                    key=lambda row: row["share_percentage"],
                    reverse=True
                )

                top_payment = shares[0]

                return (
                    f"Credit card and boleto payments accounted for "
                    f"{sum(row['share_percentage'] for row in shares if row['payment_type'] in {'credit_card', 'boleto'}):.2f}% "
                    f"of payment value. "
                    f"{top_payment['payment_type']} had the largest share "
                    f"at {top_payment['share_percentage']:.2f}%."
                )

    # --------------------------------------------------
    # Delivery performance
    # --------------------------------------------------

    if tool_name == "get_delivery_performance":

        metric = tool_args.get("metric")

        if metric == "on_time_rate":

            rates = [
                float(row.get("on_time_rate", 0))
                for row in data
                if row.get("on_time_rate") is not None
            ]

            if rates:
                average_rate = sum(rates) / len(rates)

                return (
                    f"The average on-time delivery rate "
                    f"across the returned results was "
                    f"{average_rate:.2f}%."
                )

        if metric == "average_delivery_days":

            values = [
                float(row.get("average_delivery_days", 0))
                for row in data
                if row.get("average_delivery_days") is not None
            ]

            if values:
                average = sum(values) / len(values)

                return (
                    f"The average delivery time "
                    f"across the returned results was "
                    f"{average:.2f} days."
                )

    # --------------------------------------------------
    # Generic fallback
    # --------------------------------------------------

    return (
        f"The analytics query returned {len(data)} result rows."
    )