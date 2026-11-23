CREATE TABLE IF NOT EXISTS conditioning_cabinets (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity BETWEEN 1 AND 20),
    humidity NUMERIC(4,1) NOT NULL CHECK (humidity BETWEEN 10 AND 95),
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS conditioning_assignments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    treatment_id BIGINT NOT NULL UNIQUE REFERENCES treatments(id),
    cabinet_code TEXT NOT NULL REFERENCES conditioning_cabinets(code),
    intake_humidity NUMERIC(4,1) NOT NULL CHECK (intake_humidity BETWEEN 45 AND 55),
    intake_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    vacated_at TIMESTAMPTZ,
    vacated_by TEXT,
    CHECK ((vacated_at IS NULL) = (vacated_by IS NULL))
);
CREATE INDEX IF NOT EXISTS cabinet_occupancy
    ON conditioning_assignments(cabinet_code) WHERE vacated_at IS NULL;
INSERT INTO conditioning_cabinets(code,title,capacity,humidity)
VALUES ('DRY-1','北侧平衡柜',1,49),('DRY-2','弓弦备用柜',2,60)
ON CONFLICT DO NOTHING;
