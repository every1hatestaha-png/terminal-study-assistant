import pytest
from fastapi.testclient import TestClient

import app as server


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SERVER_TOKEN", "my-test-server-token")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    return TestClient(server.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_requires_token(client):
    assert client.post("/v1/ask", json={"question": "explain C++"}).status_code == 401
    assert client.post("/v1/ask", headers={"Authorization": "Bearer wrong"}, json={"question": "explain C++"}).status_code == 401


def test_requires_configured_token(monkeypatch, client):
    monkeypatch.delenv("SERVER_TOKEN")
    result = client.post("/v1/ask", headers={"Authorization": "Bearer something"}, json={"question": "hi"})
    assert result.status_code == 503


@pytest.mark.parametrize("question", ["", "  ", "x" * 4001])
def test_invalid_question(client, question):
    result = client.post("/v1/ask", headers={"Authorization": "Bearer my-test-server-token"}, json={"question": question})
    assert result.status_code == 422


def test_history_length_limit(client):
    result = client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer my-test-server-token"},
        json={"question": "hello", "history": [{"role": "user", "content": "hi"}] * 9},
    )
    assert result.status_code == 422


def test_history_role_validation(client):
    result = client.post(
        "/v1/ask",
        headers={"Authorization": "Bearer my-test-server-token"},
        json={"question": "hello", "history": [{"role": "system", "content": "hi"}]},
    )
    assert result.status_code == 422


def test_groq_success_is_primary(client, monkeypatch):
    monkeypatch.setattr(server, "_groq_answer", lambda q, h: server.AskResponse(answer="Groq answer", model="groq/test"))
    monkeypatch.setattr(server, "_gemini_answer", lambda q, h: pytest.fail("Gemini should not run after Groq succeeds"))
    result = client.post("/v1/ask", headers={"Authorization": "Bearer my-test-server-token"}, json={"question": "What is a class?"})
    assert result.status_code == 200
    assert result.json() == {"answer": "Groq answer", "model": "groq/test"}


def test_gemini_fallback_when_groq_fails(client, monkeypatch):
    def fail_groq(q, h):
        raise RuntimeError("Groq unavailable")
    monkeypatch.setattr(server, "_groq_answer", fail_groq)
    monkeypatch.setattr(server, "_gemini_answer", lambda q, h: server.AskResponse(answer="Gemini backup", model="gemini/test"))
    result = client.post("/v1/ask", headers={"Authorization": "Bearer my-test-server-token"}, json={"question": "Explain inheritance"})
    assert result.status_code == 200
    assert result.json()["answer"] == "Gemini backup"


def test_both_providers_fail(client, monkeypatch):
    monkeypatch.setattr(server, "_groq_answer", lambda q, h: (_ for _ in ()).throw(RuntimeError("failed")))
    monkeypatch.setattr(server, "_gemini_answer", lambda q, h: (_ for _ in ()).throw(RuntimeError("failed")))
    result = client.post("/v1/ask", headers={"Authorization": "Bearer my-test-server-token"}, json={"question": "hello"})
    assert result.status_code == 502
    assert "All configured AI providers failed" in result.json()["detail"]


def test_lowercase_groq_env_is_supported(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("groq_api_key", "lowercase-key")
    monkeypatch.setenv("SERVER_TOKEN", "token")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(server, "_groq_answer", lambda q, h: server.AskResponse(answer="ok", model="groq/test"))
    result = server.get_answer("hello", [])
    assert result.answer == "ok"


def test_no_provider_configured(client, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY")
    monkeypatch.delenv("groq_api_key", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY")
    result = client.post("/v1/ask", headers={"Authorization": "Bearer my-test-server-token"}, json={"question": "hi"})
    assert result.status_code == 503
