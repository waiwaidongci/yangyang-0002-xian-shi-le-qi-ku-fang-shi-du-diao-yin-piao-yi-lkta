from fastapi import APIRouter, Depends

from core import db, require
from handover_models import Clearance, ConditionMeasurement
from handover_policy import clear_incident, sign, submit
from handover_repository import handovers

router = APIRouter(prefix="/api/condition")


@router.get("")
def slips(_=Depends(require())):
    with db() as cx:
        return handovers(cx)


@router.post("/loans/{loan_id}", status_code=201)
def write(loan_id: int, body: ConditionMeasurement, user=Depends(require("operator"))):
    with db() as cx:
        return submit(cx, loan_id, body, user["email"])


@router.post("/{slip_id}/sign")
def certify(slip_id: int, user=Depends(require("reviewer"))):
    with db() as cx:
        return sign(cx, slip_id, user["email"])


@router.post("/loans/{loan_id}/close-incident")
def close(loan_id: int, body: Clearance, user=Depends(require("reviewer"))):
    with db() as cx:
        return clear_incident(cx, loan_id, body, user["email"])
