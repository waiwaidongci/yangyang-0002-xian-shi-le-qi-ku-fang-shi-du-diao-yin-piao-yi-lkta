from fastapi import HTTPException


def cabinet(cx, code):
    row = cx.execute(
        "SELECT * FROM conditioning_cabinets WHERE code=%s FOR UPDATE", (code,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "平衡柜不存在")
    return row


def placements(cx):
    return cx.execute(
        """SELECT a.*,t.instrument_code,t.status AS treatment_state,i.name
           FROM conditioning_assignments a JOIN treatments t ON t.id=a.treatment_id
           JOIN instruments i ON i.code=t.instrument_code ORDER BY a.id DESC LIMIT 60"""
    ).fetchall()


def cabinets(cx):
    return cx.execute(
        """SELECT c.*,count(a.id) AS occupied
           FROM conditioning_cabinets c LEFT JOIN conditioning_assignments a
             ON a.cabinet_code=c.code AND a.vacated_at IS NULL
           GROUP BY c.code ORDER BY c.code"""
    ).fetchall()
