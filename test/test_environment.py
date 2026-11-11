"""Smoke tests for the Python web stack."""

from fastapi.testclient import TestClient


def testWebStackRendersUnicode(smoke_client: TestClient) -> None:
    question = "Explain iteration for n \u2265 0."

    response = smoke_client.post("/preview", json={"question": question})

    assert response.status_code == 200
    assert response.text == f"<p>{question}</p>"


def test_web_stack_rejects_missing_question(smoke_client: TestClient) -> None:
    response = smoke_client.post("/preview", json={})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "question"]
