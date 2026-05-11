# Business Case: HL7 v2 to FHIR Converter MVP

## Product Thesis
This project is a healthcare interoperability MVP that converts legacy HL7 v2 ADT messages into FHIR R4 resources with deterministic identifiers, vocabulary normalization, and warning-first observability.

It demonstrates practical integration engineering for real hospital data exchange constraints: messy source messages, local code variations, and the need for safe defaults.

## Initial Business Problem
Many healthcare organizations still exchange patient and encounter events using HL7 v2 feeds, while modern APIs and analytics workflows increasingly expect FHIR.

The gap creates expensive manual mapping work and brittle point-to-point interfaces.

Typical pain points:
- Legacy ADT payloads vary by source system and facility.
- Local coding differences can silently degrade downstream data quality.
- Identifier collisions across facilities can create unsafe merges.
- Integration failures are hard to debug without explicit warning signals.

## Project Goal
Build a local-first, testable conversion service that proves a reliable HL7 v2 to FHIR translation path for core ADT workflows.

The MVP focuses on practical correctness and operational clarity:
- parse required HL7 ADT segments,
- map to FHIR Patient and Encounter,
- normalize key vocabularies,
- preserve deterministic identity semantics,
- emit explicit warnings for non-ideal but recoverable inputs.

## Scope and Non-Goals
Current scope:
- HL7 v2 ADT messages (MSH, PID, PV1)
- FHIR R4 Bundle output with Patient and Encounter
- warning pipeline for edge cases

Not yet in scope:
- Full enterprise terminology service integration
- Full ADT event catalog and all optional segment groups
- Persistence, auth, or production deployment hardening

## What Was Implemented
Core implementation highlights:
- deterministic, collision-safe identifier strategy
- ADT trigger event mapping to Encounter.status
- vocabulary mapping framework for gender and admission class
- warnings for repeated segments, unmapped codes, and ambiguous identifiers
- environment-driven frontend API configuration
- side-by-side UI workbench for quick message/result validation

## Why This Matters in Healthcare Integrations
This project mirrors common interoperability realities:
- standards exist, but local implementation variability is high
- normalization decisions need to be explicit and testable
- safe fallback behavior and auditability are essential

The architecture intentionally treats mapping as a policy layer, not just string transformation.

## Delivery Credibility
Signals partners and buyers can quickly assess:
- risk-driven incremental commits with explicit rationale
- backend and mapping test coverage for edge cases and regressions
- reproducible local validation flow for API and UI
- documentation of production-like test feeds and expected outcomes

## Target Buyers and Users
Technical users:
- integration engineers
- platform engineers building healthcare data pipelines
- health-tech teams modernizing legacy interfaces

Business buyers:
- hospitals and health systems migrating toward FHIR-based workflows
- interoperability teams seeking lower-friction HL7 modernization paths

## Commercialization Roadmap
- broaden segment/event support beyond MVP ADT subset
- add profile-driven mapping configuration per customer/facility
- add deployment hardening (auth, rate limits, structured logging)
- add conformance checks against target FHIR profiles
