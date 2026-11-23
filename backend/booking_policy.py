from fastapi import HTTPException

from booking_repository import locked_request, overlapping
from drift import get_windows
from treatment import HOLD_DRIFT_CENTS


def require_playable(cx, instrument):
    windows = get_windows(cx, instrument["code"], 1)
    if instrument["loan_status"] != "available":
        raise HTTPException(409, "该琴停借中，完成处置复测后才能安排")
    if not windows or windows[0]["drift_cents"] is None or abs(windows[0]["drift_cents"]) >= HOLD_DRIFT_CENTS:
        raise HTTPException(409, "最新调音证据缺失或达到停借线")


def reserve(cx, loan_id, reviewer):
    instrument, request = locked_request(cx, loan_id)
    if request["state"] != "waiting":
        raise HTTPException(409, "仅候补中的借琴申请可确认")
    require_playable(cx, instrument)
    collision = overlapping(cx, request)
    if collision:
        raise HTTPException(409, f"与 {collision['code']} 的借用重叠或尚未归还，申请留在候补")
    return cx.execute(
        "UPDATE rehearsal_loans SET state='reserved',reserved_by=%s WHERE id=%s RETURNING *",
        (reviewer, loan_id),
    ).fetchone()


def cancel(cx, loan_id):
    _, request = locked_request(cx, loan_id)
    if request["state"] not in ("waiting", "reserved"):
        raise HTTPException(409, "已经领琴的申请须在交接页办理归还")
    return cx.execute(
        "UPDATE rehearsal_loans SET state='cancelled' WHERE id=%s RETURNING *", (loan_id,)
    ).fetchone()
