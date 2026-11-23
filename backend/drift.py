from math import sqrt
from statistics import mean

from psycopg.types.json import Jsonb

WINDOW_LIMIT = 12
MIN_PAIRS = 5


def get_windows(cx, code, limit=WINDOW_LIMIT):
    return cx.execute(
        """SELECT instrument_code, measured_at, humidity_percent, drift_cents
           FROM tuning_windows WHERE instrument_code = %s ORDER BY measured_at DESC LIMIT %s""",
        (code, limit),
    ).fetchall()


def rank(values):
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    result = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        midrank = (start + 1 + end) / 2
        for original_index, _ in ordered[start:end]:
            result[original_index] = midrank
        start = end
    return result


def spearman(xs, ys):
    """Pearson correlation of average ranks; return None for constant ranks."""
    ranks_x, ranks_y = rank(xs), rank(ys)
    mean_x, mean_y = mean(ranks_x), mean(ranks_y)
    centered_x = [value - mean_x for value in ranks_x]
    centered_y = [value - mean_y for value in ranks_y]
    scale = sqrt(sum(x * x for x in centered_x) * sum(y * y for y in centered_y))
    if scale == 0:
        return None
    return max(-1.0, min(1.0, sum(x * y for x, y in zip(centered_x, centered_y)) / scale))


def compute(cx, code):
    windows = get_windows(cx, code)
    points = [
        {
            "window": row["measured_at"].isoformat(),
            "humidity": float(row["humidity_percent"]),
            "drift": float(row["drift_cents"]),
        }
        for row in reversed(windows)
        if row["humidity_percent"] is not None and row["drift_cents"] is not None
    ]
    status, rho = "insufficient", None
    if len(points) >= MIN_PAIRS:
        rho = spearman([p["humidity"] for p in points], [p["drift"] for p in points])
        status = "computed" if rho is not None else "constant"
    return cx.execute(
        """INSERT INTO drift_assessments
           (instrument_code, pair_count, missing_count, rho, status, points)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
        (code, len(points), len(windows) - len(points), rho, status, Jsonb(points)),
    ).fetchone()
