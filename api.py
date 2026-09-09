from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent.factory import get_agent
from dashboard.service import (
    pin_query_result,
    get_dashboard,
    refresh_pinned_chart,
    unpin_chart,
)


app = FastAPI(
    title="E-Commerce Analytics Chatbot",
    version="0.1.0",
)


class QueryRequest(BaseModel):
    query: str


class PinRequest(BaseModel):
    query: str
    result: dict


@app.get("/")
async def root():
    return {
        "message": "E-Commerce Analytics Chatbot API",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/ask")
async def ask(request: QueryRequest):
    agent = get_agent()
    result = await agent.ask(request.query)
    return result


@app.post("/dashboard/pin")
async def pin_dashboard_chart(request: PinRequest):

    try:
        pinned_chart = pin_query_result(
            query=request.query,
            result=request.result,
        )

        return {
            "success": True,
            "chart": pinned_chart.__dict__,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.get("/dashboard")
async def dashboard():

    charts = get_dashboard()

    return {
        "success": True,
        "charts": [chart.__dict__ for chart in charts],
        "count": len(charts),
    }


@app.post("/dashboard/{chart_id}/refresh")
async def refresh_dashboard_chart(chart_id: int):
    try:
        agent = get_agent()

        result = await refresh_pinned_chart(
            chart_id=chart_id,
            agent=agent,
        )

        return result

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.delete("/dashboard/{chart_id}")
async def delete_dashboard_chart(chart_id: int):
    deleted = unpin_chart(chart_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Pinned chart {chart_id} was not found.",
        )

    return {
        "success": True,
        "chart_id": chart_id,
        "message": "Chart unpinned successfully.",
    }