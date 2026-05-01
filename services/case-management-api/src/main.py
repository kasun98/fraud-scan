import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../decision-aggregator/src"))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database import (
    get_decisions,
    get_decision_by_id,
    get_stats,
    get_chart_data,
    get_map_data,
    save_review,
)
from models import DecisionRecord, ReviewRequest, ReviewResponse, StatsResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)
logger = logging.getLogger("case-management-api")

app = FastAPI(
    title="Case Management API",
    description="Fraud case review and analyst feedback endpoints",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}




@app.get("/api/v1/stats")
def get_dashboard_stats():
    return get_stats()

@app.get("/api/v1/chart_data")
def chart_data():
    return get_chart_data()

@app.get("/api/v1/map_data")
def map_data():
    return get_map_data()

@app.get("/api/v1/cases", response_model=list[DecisionRecord])
def list_cases(
    limit:    int         = Query(50, ge=1, le=200),
    offset:   int         = Query(0,  ge=0),
    decision: str | None  = Query(
        None,
        pattern="^(APPROVE|REVIEW|BLOCK|CONFIRMED_FRAUD)(,(APPROVE|REVIEW|BLOCK|CONFIRMED_FRAUD))*$",
    ),
    user_id:  str | None  = Query(None),
):
    parsed_decision = [d.strip() for d in decision.split(',')] if decision else None
    rows = get_decisions(
        limit=limit,
        offset=offset,
        decision_filter=parsed_decision,
        user_id=user_id,
    )
    return [_serialize(r) for r in rows]


@app.get("/api/v1/cases/{transaction_id}", response_model=DecisionRecord)
def get_case(transaction_id: str):
    row = get_decision_by_id(transaction_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return _serialize(row)


@app.post("/api/v1/cases/{transaction_id}/review", response_model=ReviewResponse)
def submit_review(transaction_id: str, body: ReviewRequest):
    row = get_decision_by_id(transaction_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    valid = {"CONFIRMED_FRAUD", "FALSE_POSITIVE", "NEEDS_INFO"}
    if body.analyst_decision not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"analyst_decision must be one of {valid}",
        )

    save_review({
        "transaction_id":   transaction_id,
        "analyst_id":       body.analyst_id,
        "analyst_decision": body.analyst_decision,
        "notes":            body.notes,
    })

    from datetime import datetime, timezone
    return ReviewResponse(
        transaction_id=transaction_id,
        analyst_id=body.analyst_id,
        analyst_decision=body.analyst_decision,
        notes=body.notes,
        reviewed_at=datetime.now(timezone.utc),
    )


def _serialize(row: dict) -> dict:
    """Convert Postgres types to JSON-serializable types."""
    result = dict(row)
    if isinstance(result.get("triggered_rules"), str):
        import json
        result["triggered_rules"] = json.loads(result["triggered_rules"])
    if result.get("triggered_rules") is None:
        result["triggered_rules"] = []
    for field in ("transaction_id",):
        if result.get(field):
            result[field] = str(result[field])
    return result