from pydantic import BaseModel, Field
from typing import Any, List


class ConvertRequest(BaseModel):
    hl7_message: str = Field(..., min_length=1)


class ConvertResponse(BaseModel):
    bundle: dict[str, Any]
    warnings: List[str]
