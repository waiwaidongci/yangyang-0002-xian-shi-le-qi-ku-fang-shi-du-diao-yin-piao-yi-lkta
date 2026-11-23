from datetime import timedelta
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, StringConstraints, model_validator

LoanCode = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9-]{3,24}$")]


class RehearsalRequest(BaseModel):
    code: LoanCode
    instrument_code: LoanCode
    ensemble: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]
    use_from: AwareDatetime
    use_until: AwareDatetime

    @model_validator(mode="after")
    def interval(self):
        duration = self.use_until - self.use_from
        if not timedelta(minutes=30) <= duration <= timedelta(days=7):
            raise ValueError("借用时段须在半小时至七天之间")
        return self
