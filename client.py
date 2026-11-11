"""Dependency-free HTTPS terminal client for the study assistant service."""

import argparse
import getpass
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class ClientError(Exception):
    """A user-readable network or API problem."""


def validate_url(raw: str) -> str:
    url = raw.strip().rstrip("/")
    parts = urlsplit(url)
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ClientError("Provide only an HTTPS server origin, e.g. https://your-project.vercel.app")
    if parts.scheme != "https" and not (parts.scheme == "http" and parts.hostname in local_hosts):
        raise ClientError("HTTPS is required outside localhost")
    return url


def request_answer(url: str, token: str, question: str, history: list[dict[str, str]]) -> str:
    if not token.strip():
        raise ClientError("Missing server access token")
    url = validate_url(url)
    payload = json.dumps({"question": question, "history": history}).encode("utf-8")
    request = Request(
        url + "/v1/ask",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=35) as response:
            body = response.read(65536)
    except HTTPError as exc:
        raw_error = exc.read(65536)
        detail = ""
        try:
            error_body = json.loads(raw_error)
            detail = error_body.get("detail") or error_body.get("error", {}).get("message", "")
            if not isinstance(detail, str):
                detail = json.dumps(detail)
        except (ValueError, TypeError):
            detail = raw_error.decode("utf-8", errors="replace").strip()

        message = {
            401: "Invalid access token",
            422: "Request rejected (invalid or too much text)",
            429: "Service rate limit reached",
            502: "AI provider unavailable",
            503: "Server missing required configuration",
        }.get(exc.code, f"Server returned HTTP {exc.code}")
        if detail:
            message += f": {detail[:500]}"
        raise ClientError(message) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ClientError(f"Connection failed: {exc.reason if isinstance(exc, URLError) else exc}") from exc
    try:
        result = json.loads(body)
        answer = result["answer"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("empty answer")
        return answer
    except (ValueError, KeyError, TypeError) as exc:
        raise ClientError("Unexpected server response") from exc


def run() -> int:
    parser = argparse.ArgumentParser(description="Talk to your own study assistant server")
    parser.add_argument("--url", default=os.getenv("TUTOR_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--ask", help="Ask one question instead of starting a chat")
    args = parser.parse_args()

    try:
        url = validate_url(args.url)
        token = os.getenv("TUTOR_TOKEN") or getpass.getpass("Server token: ")
        if not token:
            raise ClientError("A token is required")
        history: list[dict[str, str]] = []
        if args.ask:
            print(request_answer(url, token, args.ask, history))
            return 0
        print("Study assistant. Type /help for commands; /exit to quit.")
        while True:
            try:
                question = input("You > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if question.lower() in ("/exit", "/quit"):
                return 0
            if question.lower() == "/help":
                print("/clear clears chat memory, /exit quits")
                continue
            if question.lower() == "/clear":
                history.clear()
                print("History cleared")
                continue
            if not question:
                continue
            try:
                answer = request_answer(url, token, question, history)
            except ClientError as exc:
                print(f"Error: {exc}")
                continue
            print("Tutor > " + answer + "\n")
            history.extend([{"role": "user", "content": question[:2000]}, {"role": "assistant", "content": answer[:2000]}])
            history = history[-8:]
    except ClientError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
