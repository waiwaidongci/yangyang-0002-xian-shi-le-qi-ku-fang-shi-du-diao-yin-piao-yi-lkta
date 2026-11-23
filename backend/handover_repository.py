from fastapi import HTTPException

from booking_repository import locked_request


def locked_slip(cx, slip_id):
    ref = cx.execute("SELECT loan_id FROM condition_slips WHERE id=%s", (slip_id,)).fetchone()
    if ref is None:
        raise HTTPException(404, "琴况交接单不存在")
    instrument, request = locked_request(cx, ref["loan_id"])
    slip = cx.execute("SELECT * FROM condition_slips WHERE id=%s FOR UPDATE", (slip_id,)).fetchone()
    return instrument, request, slip


def handovers(cx):
    return cx.execute(
        """SELECT s.*,q.code AS loan_code,q.instrument_code,q.state,
                  pickup.drift_cents AS departure_cents, clearance.note AS clearance_note,
                  clearance.signed_by AS clearance_signer
           FROM condition_slips s JOIN rehearsal_loans q ON q.id=s.loan_id
           LEFT JOIN condition_slips pickup ON pickup.loan_id=s.loan_id
                 AND pickup.phase='pickup' AND pickup.signed_at IS NOT NULL
           LEFT JOIN condition_incident_clearances clearance ON clearance.loan_id=s.loan_id AND s.phase='return'
           ORDER BY s.id DESC LIMIT 80"""
    ).fetchall()
