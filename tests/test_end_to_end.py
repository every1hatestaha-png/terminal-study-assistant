"""Exercise terminal-to-FastAPI serialization with a mocked Groq provider."""

from fastapi.testclient import TestClient

import app as api
import client as terminal


def test_terminal_to_server_to_mock_model(monkeypatch):
    token = "test-session-token-please-keep-private"
    monkeypatch.setenv("SERVER_TOKEN", token)
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-provider-key")
    monkeypatch.delenv("groq_api_key", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def fake_groq(question, history):
        assert question == "Explain inheritance"
        assert history == []
        return api.AskResponse(
            answer="Inheritance lets a class extend another.",
            model="groq/openai/gpt-oss-120b",
        )

    monkeypatch.setattr(api, "_groq_answer", fake_groq)
    test_client = TestClient(api.app)

    def fake_client_network(request, timeout):
        response = test_client.post(
            "/v1/ask",
            headers=dict(request.header_items()),
            content=request.data,
        )
        assert response.status_code == 200, response.text

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self, limit):
                return response.content

        return Response()

    monkeypatch.setattr(terminal, "urlopen", fake_client_network)
    answer = terminal.request_answer(
        "https://study.example.com",
        token,
        "Explain inheritance",
        [],
    )
    assert answer == "Inheritance lets a class extend another."
