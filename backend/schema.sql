CREATE TABLE IF NOT EXISTS instruments (
    code TEXT PRIMARY KEY CHECK (code ~ '^[A-Z]{2}-[0-9]{3}$'),
    name TEXT NOT NULL,
    cabinet TEXT NOT NULL,
    reference_hz REAL NOT NULL CHECK (reference_hz BETWEEN 415 AND 445),
    loan_status TEXT NOT NULL DEFAULT 'available' CHECK (loan_status IN ('available', 'held'))
);

CREATE TABLE IF NOT EXISTS tuning_windows (
    instrument_code TEXT NOT NULL REFERENCES instruments(code),
    measured_at TIMESTAMPTZ NOT NULL,
    humidity_percent NUMERIC(4,1) CHECK (humidity_percent BETWEEN 10 AND 95),
    drift_cents NUMERIC(5,1) CHECK (drift_cents BETWEEN -150 AND 150),
    PRIMARY KEY (instrument_code, measured_at),
    CHECK (humidity_percent IS NOT NULL OR drift_cents IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS treatments (
    id BIGSERIAL PRIMARY KEY,
    instrument_code TEXT NOT NULL REFERENCES instruments(code),
    opened_window TIMESTAMPTZ NOT NULL,
    opened_by TEXT NOT NULL,
    intervention TEXT NOT NULL CHECK (intervention IN ('rehouse', 'retune', 'condition')),
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'applied', 'released')),
    applied_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    released_by TEXT,
    first_retest TIMESTAMPTZ,
    last_retest TIMESTAMPTZ,
    FOREIGN KEY (instrument_code, opened_window) REFERENCES tuning_windows(instrument_code, measured_at),
    FOREIGN KEY (instrument_code, first_retest) REFERENCES tuning_windows(instrument_code, measured_at),
    FOREIGN KEY (instrument_code, last_retest) REFERENCES tuning_windows(instrument_code, measured_at),
    CHECK ((status = 'released') = (first_retest IS NOT NULL AND last_retest IS NOT NULL)),
    CHECK (
        (status = 'open' AND applied_at IS NULL AND released_at IS NULL AND released_by IS NULL)
        OR (status = 'applied' AND applied_at IS NOT NULL AND released_at IS NULL AND released_by IS NULL)
        OR (status = 'released' AND applied_at IS NOT NULL AND released_at IS NOT NULL AND released_by IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS one_active_treatment_per_instrument
    ON treatments (instrument_code) WHERE status <> 'released';

CREATE TABLE IF NOT EXISTS drift_assessments (
    id BIGSERIAL PRIMARY KEY,
    instrument_code TEXT NOT NULL REFERENCES instruments(code),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    pair_count INTEGER NOT NULL CHECK (pair_count BETWEEN 0 AND 12),
    missing_count INTEGER NOT NULL CHECK (missing_count BETWEEN 0 AND 12),
    rho DOUBLE PRECISION CHECK (rho BETWEEN -1 AND 1),
    status TEXT NOT NULL CHECK (status IN ('computed', 'insufficient', 'constant')),
    points JSONB NOT NULL,
    CHECK (pair_count + missing_count <= 12),
    CHECK ((status = 'computed') = (rho IS NOT NULL))
);
