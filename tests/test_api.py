
import io
import json

import pytest
from fastapi.testclient import TestClient

import app as server


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SERVER_TOKEN", "my-test-server-token")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    return TestClient(server.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_requires_token(client):
    assert client.post(
        "/v1/ask",
        json={"question": "explain C++"},
    ).status_code == 401

    assert client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer wrong"},
        json={"question": "explain C++"},
    ).status_code == 401


def test_requires_configured_token(monkeypatch, client):
    monkeypatch.delenv("SERVER_TOKEN")
    result = client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer something"},
        json={"question": "hi"},
    )
    assert result.status_code == 503


def test_successful_request(client, monkeypatch):
    monkeypatch.setattr(
        server,
        "get_answer",
        lambda q, h: server.AskResponse(
            answer=f"Explained {q}",
            model="fake-model",
        ),
    )

    result = client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer my-test-server-token"},
        json={"question": "What is a class?", "history": []},
    )

    assert result.status_code == 200
    assert result.json() == {
        "answer": "Explained What is a class?",
        "model": "fake-model",
    }


@pytest.mark.parametrize("question", ["", "  ", "x" * 4001])
def test_invalid_question(client, question):
    result = client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer my-test-server-token"},
        json={"question": question},
    )
    assert result.status_code == 422


def test_history_length_limit(client):
    result = client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer my-test-server-token"},
        json={
            "question": "hello",
            "history": [{"role": "user", "content": "hi"}] * 9,
        },
    )
    assert result.status_code == 422


def test_history_role_validation(client):
    result = client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer my-test-server-token"},
        json={
            "question": "hello",
            "history": [{"role": "system", "content": "hi"}],
        },
    )
    assert result.status_code == 422


def test_api_not_configured(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")

    result = client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer my-test-server-token"},
        json={"question": "hi"},
    )

    assert result.status_code == 503
    assert "Gemini API is not configured" in result.text


def test_provider_response(client, monkeypatch):
    def fake_urlopen(request, timeout):
        assert "generativelanguage.googleapis.com" in request.full_url
        assert request.get_header("X-goog-api-key") == "test-gemini-key"

        data = json.loads(request.data)

        assert data["contents"][-1]["parts"][0]["text"] == "What is a class?"
        assert data["generationConfig"]["maxOutputTokens"] == 600

        response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "A class describes an object."}
                        ]
                    }
                }
            ]
        }

        return io.BytesIO(json.dumps(response_data).encode())

    monkeypatch.setattr(server, "urlopen", fake_urlopen)

    result = client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer my-test-server-token"},
        json={"question": "What is a class?"},
    )

    assert result.status_code == 200
    assert result.json()["answer"] == "A class describes an object."


def test_empty_provider_response(client, monkeypatch):
    monkeypatch.setattr(
        server,
        "urlopen",
        lambda request, timeout: io.BytesIO(
            b'{"candidates": []}'
        ),
    )

    result = client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer my-test-server-token"},
        json={"question": "hello"},
    )

    assert result.status_code == 502
