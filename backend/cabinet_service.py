from fastapi import HTTPException

from cabinet_repository import cabinet
from treatment import SAFE_RH, lock_treatment


def admit(cx, body):
    treatment = lock_treatment(cx, body.treatment_id)
    if treatment["status"] == "released" or treatment["intervention"] not in ("rehouse", "condition"):
        raise HTTPException(409, "仅未结束的换柜或柜内调湿单可占用平衡柜")
    box = cabinet(cx, body.cabinet_code)
    if not SAFE_RH[0] <= box["humidity"] <= SAFE_RH[1]:
        raise HTTPException(409, "平衡柜湿度在 45%–55% 之外")
    occupied = cx.execute(
        "SELECT count(*) AS n FROM conditioning_assignments WHERE cabinet_code=%s AND vacated_at IS NULL",
        (box["code"],),
    ).fetchone()["n"]
    if occupied >= box["capacity"]:
        raise HTTPException(409, "该平衡柜已满")
    row = cx.execute(
        """INSERT INTO conditioning_assignments(treatment_id,cabinet_code,intake_humidity)
           VALUES (%s,%s,%s) ON CONFLICT(treatment_id) DO NOTHING RETURNING *""",
        (treatment["id"], box["code"], box["humidity"]),
    ).fetchone()
    if row is None:
        raise HTTPException(409, "该处置已经登记过平衡柜")
    return row


def vacate(cx, assignment_id, reviewer):
    row = cx.execute(
        "SELECT * FROM conditioning_assignments WHERE id=%s", (assignment_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "占柜记录不存在")
    treatment = lock_treatment(cx, row["treatment_id"])
    cabinet(cx, row["cabinet_code"])
    if treatment["status"] != "released":
        raise HTTPException(409, "处置尚未通过原有复测，不能释放柜位")
    result = cx.execute(
        """UPDATE conditioning_assignments SET vacated_at=now(),vacated_by=%s
           WHERE id=%s AND vacated_at IS NULL RETURNING *""",
        (reviewer, assignment_id),
    ).fetchone()
    if result is None:
        raise HTTPException(409, "该柜位已释放")
    return result
