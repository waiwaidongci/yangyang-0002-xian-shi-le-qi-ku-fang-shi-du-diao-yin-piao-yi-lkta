from fastapi import HTTPException

from booking_policy import require_playable
from booking_repository import locked_request
from handover_repository import locked_slip

DRIFT_CHANGE_LIMIT = 8


def check_phase(request, phase):
    expected = "reserved" if phase == "pickup" else "out"
    if request["state"] != expected:
        raise HTTPException(409, "领琴须已预约，归还须已签领")


def submit(cx, loan_id, body, actor):
    _, loan = locked_request(cx, loan_id)
    check_phase(loan, body.phase)
    return cx.execute(
        """INSERT INTO condition_slips(loan_id,phase,bridge_ok,case_ok,drift_cents,note,operator)
           VALUES (%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT(loan_id,phase) WHERE signed_at IS NULL DO UPDATE SET
             bridge_ok=excluded.bridge_ok,case_ok=excluded.case_ok,drift_cents=excluded.drift_cents,
             note=excluded.note,operator=excluded.operator,submitted_at=now()
           RETURNING *""",
        (loan_id, body.phase, body.bridge_ok, body.case_ok, body.drift_cents, body.note, actor),
    ).fetchone()


def sign(cx, slip_id, reviewer):
    instrument, request, slip = locked_slip(cx, slip_id)
    check_phase(request, slip["phase"])
    if slip["signed_at"] is not None:
        raise HTTPException(409, "交接单已经签署")
    sounds_safe = slip["bridge_ok"] and slip["case_ok"]
    if slip["phase"] == "pickup":
        require_playable(cx, instrument)
        if not sounds_safe or abs(slip["drift_cents"]) > 5:
            raise HTTPException(409, "领琴必须琴桥和琴盒完好且调音偏差不超过 5 音分")
        already_out = cx.execute(
            "SELECT 1 FROM rehearsal_loans WHERE instrument_code=%s AND state IN ('out','incident')",
            (instrument["code"],),
        ).fetchone()
        if already_out:
            raise HTTPException(409, "这把琴上一场尚未交回")
        state = "out"
    else:
        pickup = cx.execute(
            "SELECT drift_cents FROM condition_slips WHERE loan_id=%s AND phase='pickup' AND signed_at IS NOT NULL",
            (request["id"],),
        ).fetchone()
        safe = sounds_safe and abs(slip["drift_cents"] - pickup["drift_cents"]) <= DRIFT_CHANGE_LIMIT
        state = "returned" if safe else "incident"
    cx.execute("UPDATE rehearsal_loans SET state=%s WHERE id=%s", (state, request["id"]))
    saved = cx.execute(
        "UPDATE condition_slips SET signed_by=%s,signed_at=now() WHERE id=%s RETURNING *",
        (reviewer, slip_id),
    ).fetchone()
    return {**saved, "loan_state": state}


def clear_incident(cx, loan_id, body, actor):
    instrument, request = locked_request(cx, loan_id)
    if request["state"] != "incident":
        raise HTTPException(409, "仅异常归还的借琴记录可以归档")
    require_playable(cx, instrument)
    if not body.bridge_ok or not body.case_ok or abs(body.drift_cents) > 5:
        raise HTTPException(409, "异常归档要求琴桥、琴盒复检合格且漂移在 ±5 音分内")
    cx.execute(
        """INSERT INTO condition_incident_clearances
           (loan_id,checked_bridge,checked_case,corrected_cents,note,signed_by)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (loan_id, body.bridge_ok, body.case_ok, body.drift_cents, body.note, actor),
    )
    return cx.execute("UPDATE rehearsal_loans SET state='returned' WHERE id=%s RETURNING *", (loan_id,)).fetchone()
