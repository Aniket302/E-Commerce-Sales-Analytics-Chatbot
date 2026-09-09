TOOL_DEFINITIONS = [
    {
        "name": "get_order_trends",
        "description": (
            "Analyze e-commerce order trends over time. "
            "Use this for questions about revenue, order volume, "
            "or average order value by day, week, month, or year."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format."
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format."
                },
                "metrics": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "revenue",
                            "order_count",
                            "average_order_value"
                        ]
                    },
                    "description": "Metrics to calculate."
                },
                "group_by": {
                    "type": "string",
                    "enum": [
                        "day",
                        "week",
                        "month",
                        "year"
                    ],
                    "description": "Time granularity."
                }
            },
            "required": [
                "start_date",
                "end_date",
                "metrics",
                "group_by"
            ]
        }
    },

    {
        "name": "get_category_performance",
        "description": (
            "Analyze product category performance by revenue, "
            "order count, freight value, or average review score."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string"
                },
                "end_date": {
                    "type": "string"
                },
                "metric": {
                    "type": "string",
                    "enum": [
                        "revenue",
                        "order_count",
                        "freight_value",
                        "average_review_score"
                    ]
                },
                "category": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional English product category."
                    )
                },
                "categories": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "string"
                    },
                    "description": (
                        "Optional list of English product categories."
                    )
                },
                "limit": {
                    "type": "integer"
                },
                "sort": {
                    "type": "string",
                    "enum": [
                        "asc",
                        "desc"
                    ]
                }
            },
            "required": [
                "start_date",
                "end_date",
                "metric"
            ]
        }
    },

    {
        "name": "get_seller_performance",
        "description": (
            "Analyze seller performance. "
            "Use this for seller revenue, order count, review scores, "
            "delivery speed, or seller state. "
            "Use 'metrics' when the user asks to compare multiple seller "
            "metrics for the same sellers. "
            "For example, use metrics=['average_delivery_days', "
            "'average_review_score'] for questions about whether faster "
            "delivery is associated with better reviews. "
            "When comparing multiple metrics, the tool returns them at the "
            "same seller_id grain."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format."
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format."
                },
                "metric": {
                    "type": "string",
                    "enum": [
                        "revenue",
                        "order_count",
                        "average_review_score",
                        "average_delivery_days"
                    ],
                    "description": (
                        "Single metric to analyze. "
                        "Use metrics instead when comparing multiple metrics."
                    )
                },
                "metrics": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "revenue",
                            "order_count",
                            "average_review_score",
                            "average_delivery_days"
                        ]
                    },
                    "description": (
                        "Multiple metrics to return at the same seller level."
                    )
                },
                "state": {
                    "type": "string",
                    "description": (
                        "Brazilian seller state code such as SP, RJ, or MG."
                    )
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximum number of sellers to return. "
                        "Use a large limit or omit the limit for relationship analysis."
                    )
                },
                "sort": {
                    "type": "string",
                    "enum": [
                        "asc",
                        "desc"
                    ]
                }
            },
            "required": [
                "start_date",
                "end_date"
            ]
        }
    },

    {
        "name": "get_review_analysis",
        "description": (
            "Analyze customer reviews. "
            "Use this for review score distribution, "
            "average review score, review count, "
            "or review response time. "
            "Use group_by='month' for review trends over time. "
            "Use group_by='customer_state' for review scores by customer state. "
            "Use group_by='category' for review scores by product category."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string"
                },
                "end_date": {
                    "type": "string"
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Optional product category in English. "
                        "Use the translated English category name."
                    )
                },
                "group_by": {
                    "type": "string",
                    "enum": [
                        "month",
                        "customer_state",
                        "category"
                    ],
                    "description": (
                        "Optional dimension for grouped review analysis."
                    )
                },
                "metric": {
                    "type": "string",
                    "enum": [
                        "score_distribution",
                        "average_review_score",
                        "review_count",
                        "average_response_time_hours"
                    ]
                },
                "limit": {
                    "type": "integer"
                },
                "sort": {
                    "type": "string",
                    "enum": [
                        "asc",
                        "desc"
                    ]
                }
            },
            "required": [
                "start_date",
                "end_date",
                "metric"
            ]
        }
    },

    {
        "name": "get_payment_breakdown",
        "description": (
            "Analyze payment behavior. "
            "Use this for payment value, payment count, "
            "installments, payment types, or payment trends by month."
            "Use payment_value grouped by payment_type for questions about the share or proportion of payment types."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string"
                },
                "end_date": {
                    "type": "string"
                },
                "metric": {
                    "type": "string",
                    "enum": [
                        "payment_value",
                        "payment_count",
                        "average_installments"
                    ]
                },
                "group_by": {
                    "type": "string",
                    "enum": [
                        "payment_type",
                        "month"
                    ]
                },
                "limit": {
                    "type": "integer"
                },
                "sort": {
                    "type": "string",
                    "enum": [
                        "asc",
                        "desc"
                    ]
                }
            },
            "required": [
                "start_date",
                "end_date",
                "metric",
                "group_by"
            ]
        }
    },

    {
        "name": "get_delivery_performance",
        "description": (
            "Analyze delivery performance. "
            "Use average_delivery_days for questions specifically about "
            "delivery time. "
            "Use average_delay_days for questions about delivery delay. "
            "Use on_time_rate for delivery reliability/performance questions. "
            "For 'worst delivery performance', use on_time_rate with sort='asc'. "
            "For 'best delivery performance', use on_time_rate with sort='desc'. "
            "When the user asks about states, use customer_state unless they "
            "explicitly ask about seller locations. "
            "If no date range is specified, use the full dataset: "
            "2016-09-04 through 2018-10-17."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string"
                },
                "end_date": {
                    "type": "string"
                },
                "metric": {
                    "type": "string",
                    "enum": [
                        "average_delivery_days",
                        "average_delay_days",
                        "on_time_rate",
                        "order_count"
                    ]
                },
                "group_by": {
                    "type": "string",
                    "enum": [
                        "month",
                        "seller_state",
                        "customer_state",
                        "route"
                    ]
                },
                "limit": {
                    "type": "integer"
                },
                "sort": {
                    "type": "string",
                    "enum": [
                        "asc",
                        "desc"
                    ]
                }
            },
            "required": [
                "start_date",
                "end_date",
                "metric",
                "group_by"
            ]
        }
    }
]