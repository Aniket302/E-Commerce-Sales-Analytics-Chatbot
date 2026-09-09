# E-Commerce Sales Analytics Chatbot

An AI-powered analytics chatbot for the **Brazilian E-Commerce Public
Dataset by Olist**. The application converts natural-language business
questions into structured analytics using an LLM, MCP tools, SQLite, and
interactive charts.

## Features

-   Natural-language e-commerce analytics queries
-   SQLite-backed analytics over the Olist dataset
-   Standalone **FastMCP** server with six analytics tools
-   LLM agent with native tool calling
-   Rule-based fallback agent
-   Configurable `AGENT_MODE=llm|fallback`
-   Configurable LLM timeout
-   Automatic parameter extraction from natural language
-   Product category translation from Portuguese to English
-   Automatic chart selection based on data shape
-   Support for ambiguous queries with alternative chart options
-   Persistent chart pinning and refresh
-   Significant-change detection for refreshed pinned charts
-   FastAPI backend
-   Streamlit dashboard
-   Docker Compose deployment

## Architecture

``` text
                    ┌─────────────────────┐
                    │       Browser       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Streamlit Dashboard │
                    │      :8501          │
                    └──────────┬──────────┘
                               │ HTTP
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI API      │
                    │      :8000          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     LLM Agent       │
                    │ Groq / fallback     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      FastMCP        │
                    │   analytics tools   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    SQLite / Olist   │
                    │      olist.db       │
                    └─────────────────────┘
```

FastMCP runs in-process with the backend; it does not require a separate
container.

## Project Structure

``` text
DSI/
├── agent/
│   ├── __init__.py
│   ├── fallback_agent.py
│   ├── interface.py
│   ├── llm_agent.py
│   ├── multi_tool_analysis.py
│   ├── orchestration.py
│   ├── chart_rules.py
│   ├── response_builder.py
│   └── tool_definitions.py
│
├── dashboard/
│   ├── __init__.py
│   ├── app.py
│   ├── chart_renderer.py
│   ├── models.py
│   ├── service.py
│   └── storage.py
│
├── database/
│   ├── olist.db
│   └── schema.sql
│
├── mcp_server/
│   ├── __init__.py
│   ├── database.py
│   ├── server.py
│   └── tools/
│       ├── __init__.py
│       ├── orders.py
│       ├── categories.py
│       ├── sellers.py
│       ├── reviews.py
│       ├── payments.py
│       └── delivery.py
│
├── scripts/
├── api.py
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── .gitignore
└── pyproject.toml
```

## MCP Analytics Tools

The MCP layer exposes six analytics tools:

| Tool | Purpose |
|---|---|
| `get_order_trends` | Revenue, order volume, and average order value over time |
| `get_category_performance` | Category revenue, orders, freight, and review performance |
| `get_seller_performance` | Seller revenue, orders, ratings, and delivery performance |
| `get_review_analysis` | Review scores, distributions, counts, and response times |
| `get_payment_breakdown` | Payment types, payment values, counts, and installments |
| `get_delivery_performance` | Delivery time, delay, on-time rate, and route/state performance |

### Category Translation

Product categories are translated through the Olist category translation
table before category results are returned.

The application uses the English category name when presenting category
analytics.

## Agent Modes

The application supports two agent modes.

### LLM Mode

``` env
AGENT_MODE=llm
```

The LLM uses native tool calling to select and parameterize the
appropriate MCP analytics tools.

The current configuration uses Groq:

``` env
GROQ_MODEL=openai/gpt-oss-120b
```

### Fallback Mode

``` env
AGENT_MODE=fallback
```

The fallback agent uses deterministic keyword matching and predefined
rules. This allows the application to continue answering supported
analytics questions when an LLM is unavailable.

## Environment Variables

Create `.env` from `.env.example`.

Example:

``` env
GROQ_API_KEY=your_groq_api_key

GROQ_MODEL=openai/gpt-oss-120b

AGENT_MODE=llm

LLM_TIMEOUT=30

MCP_TIMEOUT=30

API_HOST=0.0.0.0
API_PORT=8000

STREAMLIT_HOST=0.0.0.0
STREAMLIT_PORT=8501

API_BASE_URL=http://localhost:8000
```

## Running with Docker

Docker Compose is the recommended way to run the complete application.

### Prerequisites

-   Docker Desktop
-   A Groq API key

### Setup

1.  Create `.env` from `.env.example`.
2.  Add your Groq API key to `.env`.
3.  Create the database/olist.db file using the script:

``` powershell
python scripts/load_db.py
```

4.  Start the application:

``` powershell
docker compose up
```

Docker Compose builds and starts both services:

``` text
backend     → FastAPI
dashboard   → Streamlit
```

No manual database initialization or MCP server startup is required.

### Access the Application

Open:

``` text
http://localhost:8501
```

The FastAPI backend is available at:

``` text
http://localhost:8000
```

## Running Locally Without Docker

If you want to run the application directly from the Python environment:

### Install dependencies

``` powershell
pip install -e .
```

### Start the backend

``` powershell
uvicorn api:app --host 0.0.0.0 --port 8000
```

### Start the dashboard

In another terminal:

``` powershell
streamlit run dashboard/app.py
```

Then open:

``` text
http://localhost:8501
```

## Example Queries

The chatbot supports natural-language questions such as:

``` text
Show monthly revenue for 2017
```

``` text
What are the top 10 product categories by revenue?
```

``` text
Compare review scores across the top 5 categories by order volume
```

``` text
Which sellers in São Paulo have the highest revenue?
```

``` text
Show payment types for 2017
```

``` text
What was the on-time delivery rate by month in 2017?
```

``` text
Show how order volume and average review score changed month by month in 2017
```

## Natural-Language Parameter Handling

The agent extracts common analytical parameters from user queries.

Examples:

  User phrase            Interpretation
  ---------------------- ---------------------------------------------------
  `last year`            2017-01-01 to 2017-12-31
  `first half of 2017`   2017-01-01 to 2017-06-30
  `São Paulo`            State `SP`
  `top 10`               Limit 10, descending by relevant metric
  `worst rated`          Ascending average review score
  `electronics`          English product category through translation data
  No date range          Full available dataset

When no date range is supplied, the response states that the full
dataset was used.

## Chart Selection

Charts are selected according to the analytical shape of the result.

  Data shape                            Chart
  ------------------------------------- ------------------------
  Single metric over time               Line
  Two metrics over the same time axis   Dual-axis line
  Ranked top N                          Horizontal bar
  Category comparison in one period     Vertical bar
  Part-to-whole                         Donut
  Two continuous variables per entity   Scatter
  Review score distribution             Horizontal bar
  Ambiguous shape                       Multiple chart options

Examples:

-   Monthly revenue → line chart
-   Top categories by revenue → horizontal bar chart
-   Payment share → donut chart
-   Seller delivery time vs review score → scatter plot
-   Monthly orders vs review score → dual-axis line chart

## Dashboard

The Streamlit dashboard provides:

-   Query input
-   Analytics response
-   Returned data table
-   Automatically selected chart
-   Chart explanation
-   Pin chart functionality
-   Persistent pinned charts
-   Refresh of original pinned queries
-   Significant-change detection after refresh

Pinned charts retain their original query so the same analysis can be
re-run later.

## Guardrails

The application handles common failure cases:

### Unsupported questions

If a question cannot be answered from the Olist dataset, the application
returns a clear message and does not generate a chart.

### Empty results

If a valid query returns no rows, no chart is generated.

### Tool failures

If an analytics tool fails or times out, the response identifies the
failed source rather than silently presenting incorrect results.

### LLM fallback

The application can be switched to deterministic fallback mode:

``` env
AGENT_MODE=fallback
```

## Data

The project uses the **Brazilian E-Commerce Public Dataset by Olist**.

The SQLite database contains the imported Olist data and the required
schema, relationships, indexes, and category translation data.

The application performs analytics locally against SQLite and does not
use external APIs for the underlying e-commerce data.

## Database

The database is located at:

``` text
database/olist.db
```

The schema is documented in:

``` text
database/schema.sql
```

The database contains the core Olist entities including:

-   Orders
-   Order Items
-   Payments
-   Reviews
-   Products
-   Sellers
-   Customers
-   Product Category Translation

## Development Checks

Useful commands include:

``` powershell
python -m mcp_server.server
```

To inspect the FastMCP server:

``` powershell
fastmcp inspect mcp_server/server.py
```

To start the full Docker application:

``` powershell
docker compose up
```

To stop it:

``` powershell
docker compose down
```

To rebuild after dependency or Dockerfile changes:

``` powershell
docker compose build --no-cache
docker compose up
```

## Design Decisions

### SQLite

SQLite was selected because the assignment requires loading the Olist
CSV data into a relational database while keeping the application easy
to run locally and through Docker.

### FastMCP

FastMCP provides a simple Python implementation of the MCP server while
keeping the analytics tools clearly separated from the agent.

### Tool-Based Analytics

The LLM does not directly calculate analytics from raw data. It selects
structured MCP tools, which execute deterministic SQL queries against
SQLite.

This keeps the numerical results grounded in the database.

### LLM + Fallback Architecture

The `ILLMAgent` interface separates the LLM implementation from
deterministic fallback logic. This makes the application resilient to
LLM availability or quota problems.

### Deterministic Chart Rules

Chart selection is handled through explicit rules rather than allowing
the LLM to arbitrarily choose a visualization. This makes chart behavior
predictable and easier to validate.

### Multi-Tool Analysis

Questions requiring multiple analytical dimensions can combine results
from multiple MCP tools before chart generation.

For example:

``` text
Compare seller delivery performance with review scores
```

can combine seller delivery and review analytics and support a
scatter-plot analysis.

## Demo Flow

A recommended demo sequence is:

1.  Start the application with:

``` powershell
docker compose up
```

2.  Open:

``` text
http://localhost:8501
```

3.  Ask:

``` text
Show monthly revenue for 2017
```

4.  Ask:

``` text
What are the top 10 product categories by revenue in 2017?
```

5.  Ask:

``` text
Compare review scores across the top 5 categories by order volume
```

6.  Ask:

``` text
Show how order volume and average review score changed month by month in 2017
```

7.  Pin a chart.

8.  Refresh the pinned chart and demonstrate the change-detection
    behavior.
