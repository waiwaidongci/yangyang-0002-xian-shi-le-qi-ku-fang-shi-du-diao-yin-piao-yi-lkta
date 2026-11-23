from fastapi import APIRouter, Depends

from cabinet_models import CabinetReading, ConditioningPlacement
from cabinet_repository import cabinet, cabinets, placements
from cabinet_service import admit, vacate
from core import db, require

router = APIRouter(prefix="/api/cabinets")


@router.get("")
def overview(_=Depends(require())):
    with db() as cx:
        return {"cabinets": cabinets(cx), "placements": placements(cx)}


@router.put("/{code}/humidity")
def reading(code: str, body: CabinetReading, _=Depends(require("operator"))):
    with db() as cx:
        cabinet(cx, code)
        return cx.execute(
            """UPDATE conditioning_cabinets SET humidity=%s,checked_at=now()
               WHERE code=%s RETURNING *""", (body.humidity, code)
        ).fetchone()


@router.post("/placements", status_code=201)
def place(body: ConditioningPlacement, _=Depends(require("operator"))):
    with db() as cx:
        return admit(cx, body)


@router.post("/placements/{assignment_id}/vacate")
def clear(assignment_id: int, user=Depends(require("reviewer"))):
    with db() as cx:
        return vacate(cx, assignment_id, user["email"])
