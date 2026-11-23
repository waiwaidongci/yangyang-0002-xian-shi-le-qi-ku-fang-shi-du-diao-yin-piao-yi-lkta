from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, Field, model_validator

from core import db, enqueue, require
from drift import compute, get_windows
from treatment import (
    HOLD_DRIFT_CENTS,
    check_retest,
    lock_instrument,
    mark_applied,
    open_treatment,
    release,
)

router = APIRouter(prefix="/api")
Read = Depends(require("operator", "reviewer", "viewer"))
Operator = Depends(require("operator"))
Reviewer = Depends(require("reviewer"))
Analyst = Depends(require("operator", "reviewer"))

Humidity = Annotated[Decimal, Field(ge=10, le=95, decimal_places=1)]
Cents = Annotated[Decimal, Field(ge=-150, le=150, decimal_places=1)]


class WindowReading(BaseModel):
    measured_at: AwareDatetime
    humidity_percent: Humidity | None = None
    drift_cents: Cents | None = None

    @model_validator(mode="after")
    def check_one_channel(self):
        if (self.humidity_percent is None) == (self.drift_cents is None):
            raise ValueError("每次只录入一个来源")
        if self.measured_at.minute % 15 or self.measured_at.second or self.measured_at.microsecond:
            raise ValueError("测量窗须按 15 分钟对齐")
        return self


class InterventionOrder(BaseModel):
    instrument_code: str
    intervention: Literal["rehouse", "retune", "condition"]
    reason: str = Field(min_length=3, max_length=160)


class ApplyNote(BaseModel):
    applied_at: AwareDatetime


def require_instrument(cx, code):
    if not cx.execute("SELECT 1 FROM instruments WHERE code=%s", (code,)).fetchone():
        raise HTTPException(404, "乐器编号不存在")


@router.get("/instruments")
def inventory(_=Read):
    with db() as cx:
        return cx.execute(
            """SELECT i.*, w.measured_at, w.humidity_percent, w.drift_cents,
                      t.id AS active_treatment,
                      CASE
                        WHEN i.loan_status='held' THEN 'held'
                        WHEN w.drift_cents IS NULL THEN 'unmeasured'
                        WHEN ABS(w.drift_cents) >= %s THEN 'attention'
                        ELSE 'available'
                      END AS readiness
               FROM instruments i LEFT JOIN LATERAL (
                    SELECT measured_at, humidity_percent, drift_cents FROM tuning_windows
                    WHERE instrument_code=i.code ORDER BY measured_at DESC LIMIT 1
               ) w ON TRUE
               LEFT JOIN treatments t ON t.instrument_code=i.code AND t.status<>'released'
               ORDER BY i.code""",
            (HOLD_DRIFT_CENTS,),
        ).fetchall()


@router.get("/instruments/{code}/windows")
def windows(code: str, _=Read):
    with db() as cx:
        require_instrument(cx, code)
        return get_windows(cx, code)


@router.put("/instruments/{code}/windows")
def write_window(code: str, body: WindowReading, _=Operator):
    humidity, cents = body.humidity_percent, body.drift_cents
    with db() as cx:
        lock_instrument(cx, code)
        row = cx.execute(
            """INSERT INTO tuning_windows (instrument_code, measured_at, humidity_percent, drift_cents)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (instrument_code, measured_at) DO UPDATE SET
                   humidity_percent=COALESCE(tuning_windows.humidity_percent, EXCLUDED.humidity_percent),
                   drift_cents=COALESCE(tuning_windows.drift_cents, EXCLUDED.drift_cents)
               WHERE (EXCLUDED.humidity_percent IS NULL OR tuning_windows.humidity_percent IS NULL
                      OR tuning_windows.humidity_percent=EXCLUDED.humidity_percent)
                 AND (EXCLUDED.drift_cents IS NULL OR tuning_windows.drift_cents IS NULL
                      OR tuning_windows.drift_cents=EXCLUDED.drift_cents)
               RETURNING *""",
            (code, body.measured_at, humidity, cents),
        ).fetchone()
        if row is None:
            raise HTTPException(409, "同一来源的时窗已封存，请核对原记录")
        return row


@router.get("/instruments/{code}/assessments")
def assessments(code: str, _=Read):
    with db() as cx:
        require_instrument(cx, code)
        return cx.execute(
            """SELECT * FROM drift_assessments WHERE instrument_code=%s
               ORDER BY id DESC LIMIT 6""",
            (code,),
        ).fetchall()


@router.post("/instruments/{code}/assessments", status_code=202)
def queue_assessment(code: str, _=Analyst):
    with db() as cx:
        require_instrument(cx, code)
        return {"job_id": enqueue(cx, "spearman", {"code": code})}


@router.get("/treatments")
def treatments(_=Read):
    with db() as cx:
        records = cx.execute("SELECT * FROM treatments ORDER BY id DESC LIMIT 50").fetchall()
        return [{**record, "retest": check_retest(cx, record)} for record in records]


@router.post("/treatments", status_code=201)
def order(body: InterventionOrder, user=Operator):
    with db() as cx:
        return open_treatment(cx, body.instrument_code, body.intervention, body.reason, user["email"])


@router.post("/treatments/{record_id}/apply")
def apply(record_id: int, body: ApplyNote, _=Operator):
    with db() as cx:
        return mark_applied(cx, record_id, body.applied_at)


@router.post("/treatments/{record_id}/release")
def release_loan(record_id: int, user=Reviewer):
    with db() as cx:
        return release(cx, record_id, user["email"])


def run_job(cx, kind, payload):
    if kind != "spearman":
        raise ValueError(f"Unknown job: {kind}")
    result = compute(cx, payload["code"])
    return {key: result[key] for key in ("id", "pair_count", "missing_count", "status", "rho")}


def seed(cx):
    from seed_strings import seed_instruments

    seed_instruments(cx)
