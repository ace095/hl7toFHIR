from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.mapper import map_to_fhir_bundle
from app.models import ConvertRequest
from app.parser import HL7ParseError, parse_hl7_message

app = FastAPI(title="HL7 v2 to FHIR Converter MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/convert")
def convert_hl7_to_fhir(request: ConvertRequest) -> dict:
    try:
        segments = parse_hl7_message(request.hl7_message)
        return map_to_fhir_bundle(segments)
    except HL7ParseError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=500, detail="Unexpected conversion error.") from error


@app.get("/")
def health() -> dict:
    return {"status": "ok"}
