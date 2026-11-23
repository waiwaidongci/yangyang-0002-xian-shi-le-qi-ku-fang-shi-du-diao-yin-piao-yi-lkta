CREATE TABLE IF NOT EXISTS rehearsal_loans (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    instrument_code TEXT NOT NULL REFERENCES instruments(code),
    ensemble TEXT NOT NULL,
    use_from TIMESTAMPTZ NOT NULL,
    use_until TIMESTAMPTZ NOT NULL,
    state TEXT NOT NULL DEFAULT 'waiting' CHECK (state IN ('waiting','reserved','out','returned','incident','cancelled')),
    reserved_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (use_from < use_until)
);
CREATE INDEX IF NOT EXISTS rehearsal_active_windows
    ON rehearsal_loans(instrument_code,use_from,use_until)
    WHERE state IN ('reserved','out','incident');
CREATE UNIQUE INDEX IF NOT EXISTS one_checkout_per_instrument
    ON rehearsal_loans(instrument_code) WHERE state IN ('out','incident');
