from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


class ConditionMeasurement(BaseModel):
    phase: Literal["pickup", "return"]
    bridge_ok: bool
    case_ok: bool
    drift_cents: Decimal = Field(ge=-150, le=150, decimal_places=1)
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=180)]


class Clearance(BaseModel):
    bridge_ok: bool
    case_ok: bool
    drift_cents: Decimal = Field(ge=-150, le=150, decimal_places=1)
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=180)]
