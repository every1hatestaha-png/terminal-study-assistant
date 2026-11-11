import io
import json
from unittest.mock import patch

import pytest

import client as terminal


def test_rejects_external_http():
    with pytest.raises(terminal.ClientError, match="HTTPS"):
        terminal.validate_url("http://example.com")


def test_allows_https_and_localhost():
    assert terminal.validate_url("https://study.example.com/") == "https://study.example.com"
    assert terminal.validate_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"


@pytest.mark.parametrize("url", ["https://example.com/path", "https://user:pw@example.com", "https://example.com?token=123", "oops"])
def test_rejects_ambiguous_url(url):
    with pytest.raises(terminal.ClientError):
        terminal.validate_url(url)


def test_client_posts_auth_and_json():
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return json.dumps({"answer": "It works", "model": "fake"}).encode()

    def fake_urlopen(request, timeout):
        assert request.get_header("Authorization") == "Bearer test-token"
        assert json.loads(request.data) == {"question": "What is OOP?", "history": []}
        assert timeout == 35
        return FakeResponse()

    with patch.object(terminal, "urlopen", fake_urlopen):
        answer = terminal.request_answer("https://study.example.com", "test-token", "What is OOP?", [])
    assert answer == "It works"


def test_requires_client_token():
    with pytest.raises(terminal.ClientError, match="Missing"):
        terminal.request_answer("https://study.example.com", "  ", "hello", [])
