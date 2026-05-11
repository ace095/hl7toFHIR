# Production-Like HL7 v2 Feed Test Pack

This file is a copy/paste test pack for local UI/API validation.

It includes:
- Realistic ADT-style HL7 messages
- Edge-case messages that trigger warnings and fallbacks
- Observed API outcomes from local execution on May 10, 2026

## Does data arrive one-by-one in production?

Most interfaces send one HL7 message per event (for example admit, update, discharge). In practice, those single events can still arrive in bursts, may be retried, and may occasionally arrive out of order.

## How To Run Locally

1. Start backend on `http://127.0.0.1:8000`.
2. Open UI on `http://127.0.0.1:5173`.
3. Paste one message at a time into the textarea.
4. Click Convert and compare output against the expected behavior below.

## Test Messages

### 01 Baseline Admit (A01)

```hl7
MSH|^~\&|ADT_APP|HOSP_A|EHR|HOSP_A|20260510113010||ADT^A01|100002|P|2.5
PID|1||900001^^^HOSP_A^MR||DOE^JANE^A||19880514|F
PV1|1|I|3N^312^1^HOSP_A||||12345^SMITH^ALAN^^^^^NPI|||||||||||V000001^^^HOSP_A^VN
```

Expected highlights:
- `Encounter.status = in-progress`
- deterministic patient id `HOSP_A|MR|900001`

### 02 Unknown Gender + Unknown Admission Class

```hl7
MSH|^~\&|ADT_APP|HOSP_A|EHR|HOSP_A|20260510124500||ADT^A03|100003|P|2.5
PID|1||900001^^^HOSP_A^MR||DOE^JANE^A||19880514|X
PV1|1|Z|3N^312^1^HOSP_A||||12345^SMITH^ALAN^^^^^NPI|||||||||||V000001^^^HOSP_A^VN
```

Expected highlights:
- `Encounter.status = finished` (A03)
- warning for unmapped gender code `X`
- warning for unmapped admission class `Z`

### 03 Missing Assigning Authority in PID-3

```hl7
MSH|^~\&|ADT_APP|HOSP_A|EHR|HOSP_A|20260510130000||ADT^A01|100004|P|2.5
PID|1||900001^^^^MR||DOE^JANE^A||19880514|F
PV1|1|I|3N^312^1^HOSP_A||||12345^SMITH^ALAN^^^^^NPI|||||||||||V000001^^^HOSP_A^VN
```

Expected highlights:
- warning for missing assigning authority
- patient id falls back to `unknown|MR|900001`

### 04 Repeated PID Segment

```hl7
MSH|^~\&|ADT_APP|HOSP_A|EHR|HOSP_A|20260510131500||ADT^A01|100005|P|2.5
PID|1||900001^^^HOSP_A^MR||DOE^JANE^A||19880514|F
PID|2||900002^^^HOSP_A^MR||DOE^JANE^B||19890101|F
PV1|1|I|3N^312^1^HOSP_A||||12345^SMITH^ALAN^^^^^NPI|||||||||||V000001^^^HOSP_A^VN
```

Expected highlights:
- warning for repeated segment
- first PID is used

### 05 Multiple PID-3 Identifier Repetitions

```hl7
MSH|^~\&|ADT_APP|HOSP_A|EHR|HOSP_A|20260510133000||ADT^A01|100006|P|2.5
PID|1||A123^^^HOSP_A^MR~B999^^^ALT_HOSP^MR||DOE^JANE^A||19880514|F
PV1|1|I|3N^312^1^HOSP_A||||12345^SMITH^ALAN^^^^^NPI|||||||||||V000001^^^HOSP_A^VN
```

Expected highlights:
- warning for multiple PID-3 identifiers
- first identifier `A123` is used

### 06 Missing PV1.19 Visit Number (location fallback)

```hl7
MSH|^~\&|ADT_APP|HOSP_A|EHR|HOSP_A|20260510134500||ADT^A01|100007|P|2.5
PID|1||900001^^^HOSP_A^MR||DOE^JANE^A||19880514|F
PV1|1|I|ER^01^01
```

Expected highlights:
- warning about fallback from PV1.19 to PV1.3
- encounter id uses location component: `HOSP_A|VN|ER`

### 07 Invalid Birthdate

```hl7
MSH|^~\&|ADT_APP|HOSP_A|EHR|HOSP_A|20260510140000||ADT^A01|100008|P|2.5
PID|1||900001^^^HOSP_A^MR||DOE^JANE^A||19881340|F
PV1|1|I|3N^312^1^HOSP_A||||12345^SMITH^ALAN^^^^^NPI|||||||||||V000001^^^HOSP_A^VN
```

Expected highlights:
- no crash
- invalid `birthDate` omitted

### 08 Unsupported Message Type (negative test)

```hl7
MSH|^~\&|ORM_APP|HOSP_A|EHR|HOSP_A|20260510141500||ORM^O01|100009|P|2.5
PID|1||900001^^^HOSP_A^MR||DOE^JANE^A||19880514|F
```

Expected highlights:
- HTTP 400
- detail: `Unsupported HL7 message type 'ORM^O01'. Only ADT is supported.`

## Observed API Results (Validated Locally)

| Case | HTTP | Patient ID | Encounter ID | Encounter Status | Encounter Class | Warning Count | Error Detail |
|---|---:|---|---|---|---|---:|---|
| 01_Baseline_Admit | 200 | HOSP_A\|MR\|900001 | HOSP_A\|VN\|3N | in-progress | IMP | 1 | |
| 02_Unknown_Gender_And_Class | 200 | HOSP_A\|MR\|900001 | HOSP_A\|VN\|3N | finished | IMP | 3 | |
| 03_Missing_Assigning_Authority | 200 | unknown\|MR\|900001 | unknown\|VN\|3N | in-progress | IMP | 2 | |
| 04_Repeated_PID_Segment | 200 | HOSP_A\|MR\|900001 | HOSP_A\|VN\|3N | in-progress | IMP | 2 | |
| 05_Multiple_PID3_Repetitions | 200 | HOSP_A\|MR\|A123 | HOSP_A\|VN\|3N | in-progress | IMP | 2 | |
| 06_Missing_PV1_Visit_Number | 200 | HOSP_A\|MR\|900001 | HOSP_A\|VN\|ER | in-progress | IMP | 1 | |
| 07_Invalid_Birthdate | 200 | HOSP_A\|MR\|900001 | HOSP_A\|VN\|3N | in-progress | IMP | 1 | |
| 08_Unsupported_Message_Type | 400 |  |  |  |  | 0 | Unsupported HL7 message type 'ORM^O01'. Only ADT is supported. |

## Optional Stress Sequence (event stream order)

For stream-style simulation, send in this order:
1. 01_Baseline_Admit
2. 02_Unknown_Gender_And_Class
3. 03_Missing_Assigning_Authority
4. 04_Repeated_PID_Segment
5. 05_Multiple_PID3_Repetitions
6. 06_Missing_PV1_Visit_Number
7. 07_Invalid_Birthdate
8. 08_Unsupported_Message_Type

