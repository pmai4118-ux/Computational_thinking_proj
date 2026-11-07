"""Smoke tests for the Python web stack."""

from fastapi.testclient import TestClient


def test_web_stack_renders_vietnamese_text(smoke_client: TestClient) -> None:
    question = "Giải thích vòng lặp."

    response = smoke_client.post("/preview", json={"question": question})

    assert response.status_code == 200
    assert response.text == f"<p>{question}</p>"


def test_web_stack_rejects_missing_question(smoke_client: TestClient) -> None:
    response = smoke_client.post("/preview", json={})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "question"]
