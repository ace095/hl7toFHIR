from pydantic import BaseModel, Field


class ConvertRequest(BaseModel):
    hl7_message: str = Field(..., min_length=1)
