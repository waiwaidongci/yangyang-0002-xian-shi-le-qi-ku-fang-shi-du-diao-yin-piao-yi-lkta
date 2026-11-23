from drift import compute

ASSETS = (
    ("VA-017", "云杉中提琴", "北柜 B2", 442),
    ("VC-023", "枫背大提琴", "北柜 A1", 440),
    ("VN-041", "松纹小提琴", "南柜 C3", 442),
)
VIOLA_WINDOWS = (
    ("11-20 09:00", 43, -4),
    ("11-20 15:00", 47, 0),
    ("11-21 09:00", 47, 2),
    ("11-21 15:00", 51, 9),
    ("11-22 09:00", 53, 14),
    ("11-22 15:00", 54, None),
    ("11-23 08:00", 61, 31),
)
CELLO_WINDOWS = (
    ("11-22 08:00", 64, 22),
    ("11-22 14:00", 53, 3),
    ("11-23 08:00", 51, None),
)
VIOLIN_WINDOWS = (
    ("11-22 15:00", 50, -2),
    ("11-23 08:00", 51, 1),
)


def at(stamp):
    return f"2026-{stamp.replace(' ', 'T')}:00+08:00"


def seed_instruments(cx):
    for code, name, cabinet, reference in ASSETS:
        cx.execute(
            """INSERT INTO instruments (code, name, cabinet, reference_hz)
               VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
            (code, name, cabinet, reference),
        )
    for code, windows in zip((asset[0] for asset in ASSETS), (VIOLA_WINDOWS, CELLO_WINDOWS, VIOLIN_WINDOWS)):
        for stamp, humidity, cents in windows:
            cx.execute(
                """INSERT INTO tuning_windows (instrument_code, measured_at, humidity_percent, drift_cents)
                   VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                (code, at(stamp), humidity, cents),
            )
    if not cx.execute("SELECT 1 FROM treatments WHERE instrument_code='VC-023'").fetchone():
        cx.execute("UPDATE instruments SET loan_status='held' WHERE code='VC-023'")
        cx.execute(
            """INSERT INTO treatments (instrument_code, opened_window, opened_by, intervention, reason, status, applied_at)
               VALUES ('VC-023', %s, 'operator@demo.local', 'rehouse', '北柜受潮，移入稳定柜复测', 'applied', %s)""",
            (at("11-22 08:00"), at("11-22 09:15")),
        )
    for code, *_ in ASSETS:
        if not cx.execute("SELECT 1 FROM drift_assessments WHERE instrument_code=%s", (code,)).fetchone():
            compute(cx, code)
