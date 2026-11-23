from fastapi import APIRouter, Depends, HTTPException

from booking_models import RehearsalRequest
from booking_policy import cancel, reserve
from booking_repository import queue
from core import db, require
from treatment import lock_instrument

router = APIRouter(prefix="/api/loans")
operator = Depends(require("operator"))
reviewer = Depends(require("reviewer"))
read = Depends(require())


@router.get("")
def list_requests(_=read):
    with db() as cx:
        return queue(cx)


@router.post("", status_code=201)
def request(body: RehearsalRequest, _=operator):
    with db() as cx:
        lock_instrument(cx, body.instrument_code)
        row = cx.execute(
            """INSERT INTO rehearsal_loans(code,instrument_code,ensemble,use_from,use_until)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT(code) DO NOTHING RETURNING *""",
            (body.code, body.instrument_code, body.ensemble, body.use_from, body.use_until),
        ).fetchone()
        if not row:
            raise HTTPException(409, "该借琴单号已登记")
        return row


@router.post("/{loan_id}/reserve")
def confirm_request(loan_id: int, user=reviewer):
    with db() as cx:
        return reserve(cx, loan_id, user["email"])


@router.post("/{loan_id}/cancel")
def remove_request(loan_id: int, _=operator):
    with db() as cx:
        return cancel(cx, loan_id)
