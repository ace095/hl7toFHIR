from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_convert_endpoint_returns_fhir_bundle() -> None:
    hl7_message = (
        "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
        "PID|1||123456^^^HOSP^MR||DOE^JOHN||19800101|M\r"
        "PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345"
    )

    response = client.post("/api/v1/convert", json={"hl7_message": hl7_message})

    assert response.status_code == 200
    payload = response.json()
    assert payload["resourceType"] == "Bundle"
    assert len(payload["entry"]) == 2


def test_convert_endpoint_handles_parse_error() -> None:
    response = client.post("/api/v1/convert", json={"hl7_message": "MSH|^~\\&|A|B"})

    assert response.status_code == 400
    assert "PID" in response.json()["detail"]
