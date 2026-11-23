from datetime import timedelta

from fastapi import HTTPException

INTERVENTIONS = {"rehouse": "换柜平衡", "retune": "复调与检弦", "condition": "柜内调湿"}
STABILITY_HOURS = 4
SAFE_DRIFT_CENTS = 5
SAFE_RH = (45, 55)
HOLD_DRIFT_CENTS = 15


def lock_instrument(cx, code):
    row = cx.execute(
        "SELECT * FROM instruments WHERE code=%s FOR UPDATE", (code,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "乐器编号不存在")
    return row


def lock_treatment(cx, treatment_id):
    reference = cx.execute(
        "SELECT instrument_code FROM treatments WHERE id=%s", (treatment_id,)
    ).fetchone()
    if not reference:
        raise HTTPException(404, "处置记录不存在")
    lock_instrument(cx, reference["instrument_code"])
    return cx.execute(
        "SELECT * FROM treatments WHERE id=%s FOR UPDATE", (treatment_id,)
    ).fetchone()


def check_retest(cx, record):
    if record["applied_at"] is None:
        return {"ready": False, "reason": "请先登记处置完成时刻", "windows": []}
    if record["status"] == "released":
        rows = cx.execute(
            """SELECT measured_at, humidity_percent, drift_cents FROM tuning_windows
               WHERE instrument_code=%s AND measured_at IN (%s, %s) ORDER BY measured_at DESC""",
            (record["instrument_code"], record["first_retest"], record["last_retest"]),
        ).fetchall()
        return {"ready": True, "reason": None, "windows": rows}
    rows = cx.execute(
        """SELECT measured_at, humidity_percent, drift_cents FROM tuning_windows
           WHERE instrument_code=%s AND measured_at>%s
           ORDER BY measured_at DESC LIMIT 2""",
        (record["instrument_code"], record["applied_at"]),
    ).fetchall()
    reason = None
    if len(rows) < 2:
        reason = "处置后需要最近两个观测窗"
    elif any(row["humidity_percent"] is None or row["drift_cents"] is None for row in rows):
        reason = "最近两个时窗必须各有配对的湿度和音分记录"
    elif rows[0]["measured_at"] - rows[1]["measured_at"] < timedelta(hours=STABILITY_HOURS):
        reason = "两个复测窗间隔须至少四小时"
    elif any(
        not SAFE_RH[0] <= row["humidity_percent"] <= SAFE_RH[1]
        or abs(row["drift_cents"]) > SAFE_DRIFT_CENTS
        for row in rows
    ):
        reason = "两个复测窗均须满足湿度 45%–55% 且漂移绝对值不超过 5 音分"
    return {"ready": reason is None, "reason": reason, "windows": rows}


def open_treatment(cx, code, intervention, reason, actor):
    instrument = lock_instrument(cx, code)
    if instrument["loan_status"] != "available":
        raise HTTPException(409, "乐器已经停借，当前处置须先闭环")
    evidence = cx.execute(
        """SELECT measured_at, drift_cents FROM tuning_windows
           WHERE instrument_code=%s ORDER BY measured_at DESC LIMIT 1""",
        (code,),
    ).fetchone()
    if evidence is None or evidence["drift_cents"] is None or abs(evidence["drift_cents"]) < HOLD_DRIFT_CENTS:
        raise HTTPException(409, "最近时窗需要至少 15 音分的实测偏移才能发起处置")
    cx.execute("UPDATE instruments SET loan_status='held' WHERE code=%s", (code,))
    return cx.execute(
        """INSERT INTO treatments
           (instrument_code, opened_window, opened_by, intervention, reason)
           VALUES (%s, %s, %s, %s, %s) RETURNING *""",
        (code, evidence["measured_at"], actor, intervention, reason),
    ).fetchone()


def mark_applied(cx, treatment_id, applied_at):
    record = lock_treatment(cx, treatment_id)
    if record["status"] != "open":
        raise HTTPException(409, "需处于待处置状态")
    if applied_at <= record["opened_window"]:
        raise HTTPException(409, "处置完成时间须晚于发起处置的测量窗")
    return cx.execute(
        "UPDATE treatments SET status='applied', applied_at=%s WHERE id=%s RETURNING *",
        (applied_at, treatment_id),
    ).fetchone()


def release(cx, treatment_id, actor):
    record = lock_treatment(cx, treatment_id)
    if record["status"] != "applied":
        raise HTTPException(409, "需先登记处置完成")
    retest = check_retest(cx, record)
    if not retest["ready"]:
        raise HTTPException(409, retest["reason"])
    closed = cx.execute(
        """UPDATE treatments SET status='released', released_at=now(), released_by=%s,
               first_retest=%s, last_retest=%s WHERE id=%s RETURNING *""",
        (actor, retest["windows"][1]["measured_at"], retest["windows"][0]["measured_at"], treatment_id),
    ).fetchone()
    cx.execute(
        "UPDATE instruments SET loan_status='available' WHERE code=%s",
        (record["instrument_code"],),
    )
    return closed
