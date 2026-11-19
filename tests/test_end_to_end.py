
"""Exercise real request/response serialization across terminal and FastAPI."""

import json

from fastapi.testclient import TestClient

import app as api
import client as terminal


def test_terminal_to_server_to_mock_model(monkeypatch):
    token = "test-session-token-please-keep-private"

    monkeypatch.setenv("SERVER_TOKEN", token)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-provider-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")

    def fake_model_request(request, timeout):
        assert (
            request.full_url
            == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
        )

        body = json.loads(request.data)

        assert body["contents"][-1]["parts"][0]["text"] == "Explain inheritance"

        response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "Inheritance lets a class extend another."
                            }
                        ]
                    }
                }
            ]
        }

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return json.dumps(response_data).encode()

        return Response()

    monkeypatch.setattr(api, "urlopen", fake_model_request)

    test_client = TestClient(api.app)

    def fake_client_network(request, timeout):
        headers = dict(request.header_items())

        response = test_client.post(
            "/v1/ask",
            headers=headers,
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
