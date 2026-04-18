# HL7 v2 to FHIR Converter MVP

## Overview

This project provides a local-first MVP web app that:

- accepts pasted HL7 v2 ADT messages,
- parses key segments (`MSH`, `PID`, `PV1`),
- maps `PID` to a FHIR `Patient` and `PV1` to a FHIR `Encounter`,
- returns a FHIR R4 `Bundle` as JSON.

## Tech stack

- Backend: Python + FastAPI
- Frontend: React (Vite)
- Storage: none

## Run locally

Backend:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

## Test

```bash
pytest -q
```
