CREATE TABLE IF NOT EXISTS condition_slips (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    loan_id BIGINT NOT NULL REFERENCES rehearsal_loans(id),
    phase TEXT NOT NULL CHECK (phase IN ('pickup','return')),
    bridge_ok BOOLEAN NOT NULL,
    case_ok BOOLEAN NOT NULL,
    drift_cents NUMERIC(5,1) NOT NULL CHECK (drift_cents BETWEEN -150 AND 150),
    note TEXT NOT NULL,
    operator TEXT NOT NULL,
    signed_by TEXT,
    signed_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((signed_at IS NULL) = (signed_by IS NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS one_signed_handover_per_phase
    ON condition_slips(loan_id,phase) WHERE signed_at IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS one_pending_handover_per_phase
    ON condition_slips(loan_id,phase) WHERE signed_at IS NULL;
CREATE TABLE IF NOT EXISTS condition_incident_clearances (
    loan_id BIGINT PRIMARY KEY REFERENCES rehearsal_loans(id),
    checked_bridge BOOLEAN NOT NULL CHECK (checked_bridge),
    checked_case BOOLEAN NOT NULL CHECK (checked_case),
    corrected_cents NUMERIC(5,1) NOT NULL CHECK (corrected_cents BETWEEN -5 AND 5),
    note TEXT NOT NULL,
    signed_by TEXT NOT NULL,
    signed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
