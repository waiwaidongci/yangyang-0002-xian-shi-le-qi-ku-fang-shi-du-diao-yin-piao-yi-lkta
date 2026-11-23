from fastapi import HTTPException

from treatment import lock_instrument


def locked_request(cx, loan_id):
    ref = cx.execute("SELECT instrument_code FROM rehearsal_loans WHERE id=%s", (loan_id,)).fetchone()
    if ref is None:
        raise HTTPException(404, "借琴申请不存在")
    instrument = lock_instrument(cx, ref["instrument_code"])
    row = cx.execute("SELECT * FROM rehearsal_loans WHERE id=%s FOR UPDATE", (loan_id,)).fetchone()
    return instrument, row


def overlapping(cx, request):
    return cx.execute(
        """SELECT code FROM rehearsal_loans
           WHERE instrument_code=%s AND id<>%s AND
                 (state IN ('out','incident') OR
                  (state='reserved' AND use_from<%s AND use_until>%s))
           ORDER BY use_from LIMIT 1""",
        (request["instrument_code"], request["id"], request["use_until"], request["use_from"]),
    ).fetchone()


def queue(cx):
    return cx.execute(
        """SELECT q.*,i.name,i.loan_status,
               count(*) FILTER (WHERE q.state='waiting') OVER (
                    PARTITION BY q.instrument_code ORDER BY q.created_at,q.id
               ) AS queue_position
           FROM rehearsal_loans q JOIN instruments i ON i.code=q.instrument_code
           ORDER BY q.created_at DESC,q.id DESC LIMIT 80"""
    ).fetchall()
