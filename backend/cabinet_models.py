from decimal import Decimal

from pydantic import BaseModel, Field


class CabinetReading(BaseModel):
    humidity: Decimal = Field(ge=10, le=95, decimal_places=1)


class ConditioningPlacement(BaseModel):
    treatment_id: int = Field(ge=1)
    cabinet_code: str = Field(min_length=3, max_length=20)
