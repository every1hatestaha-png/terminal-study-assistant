"""KHZR Terminal client with secure Windows Credential Manager token storage."""

import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import keyring

DEFAULT_URL = "https://terminal-study-assistant-khzr.vercel.app"
APP_DIR = Path(os.getenv("APPDATA") or Path.home()) / "KHZR"
CONFIG = APP_DIR / "config.json"
KEYRING_SERVICE = "KHZR Terminal"
KEYRING_USERNAME = "server-access-token"


class ClientError(Exception):
    pass


def load_config():
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(data):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    # The config contains only the server URL. The access token belongs in
    # Windows Credential Manager through the keyring package.
    safe_data = {"url": data.get("url", DEFAULT_URL)}
    CONFIG.write_text(json.dumps(safe_data, indent=2), encoding="utf-8")


def get_saved_token():
    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) or ""
    except Exception as exc:
        raise ClientError("Windows Credential Manager is unavailable. Reinstall KHZR and try again.") from exc


def save_token(token):
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
    except Exception as exc:
        raise ClientError("Could not save the token securely in Windows Credential Manager.") from exc


def validate_url(raw):
    url = raw.strip().rstrip("/")
    parts = urlsplit(url)
    if not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ClientError("Set a server origin such as https://your-project.vercel.app")
    if parts.scheme != "https" and not (parts.scheme == "http" and parts.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ClientError("HTTPS is required outside localhost")
    return url


def setup(config):
    print("\nKHZR TERMINAL SETUP")
    print("Your access token will be saved in Windows Credential Manager.")
    url = input(f"Server URL [{config.get('url', DEFAULT_URL)}]: ").strip() or config.get("url", DEFAULT_URL)
    url = validate_url(url)
    token = getpass.getpass("Server access token (one time on this computer): ").strip()
    if not token:
        raise ClientError("A non-empty token is required.")
    save_token(token)
    config["url"] = url
    save_config(config)
    print("Secure setup saved.")
    print("Next time, open CMD anywhere and type: khzr")
    return config


def request_answer(url, token, question, history):
    token = (token or "").strip()
    if not token:
        raise ClientError("Missing access token. Run: khzr --setup")
    payload = json.dumps({"question": question, "history": history}).encode("utf-8")
    request = Request(url + "/v1/ask", data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
        "X-Study-Token": token,
        "Accept": "application/json",
    })
    try:
        with urlopen(request, timeout=55) as response:
            result = json.loads(response.read(65536))
    except HTTPError as exc:
        raw = exc.read(65536).decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw).get("detail", raw)
        except ValueError:
            detail = raw
        messages = {
            401: "Access token is incorrect. Run: khzr --setup",
            404: "The API route was not found. The hosted deployment may need fixing.",
            429: "Rate limit reached. Wait a moment and retry.",
            502: "Both AI providers failed. Check provider keys and server logs.",
            503: "Server configuration is incomplete. Check Vercel environment variables.",
        }
        raise ClientError(messages.get(exc.code, f"Server HTTP {exc.code}") + (f"\n{str(detail)[:400]}" if detail else "")) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ClientError(f"Could not connect: {exc}") from exc
    except (ValueError, TypeError) as exc:
        raise ClientError("The server returned an invalid response.") from exc
    answer = result.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ClientError("The AI returned an empty response.")
    model = result.get("model", "AI")
    print(f"[Provider: {model}]")
    return answer


def run():
    parser = argparse.ArgumentParser(prog="khzr", description="KHZR Terminal AI assistant")
    parser.add_argument("--setup", action="store_true", help="Save or replace server settings")
    parser.add_argument("--ask", help="Ask one question and exit")
    parser.add_argument("--url", help="Override server URL for this session", default=None)
    args = parser.parse_args()
    config = load_config()
    try:
        token = get_saved_token()
        if args.setup or not token:
            config = setup(config)
            token = get_saved_token()
        url = validate_url(args.url or config.get("url", DEFAULT_URL))
        if not token:
            raise ClientError("Run khzr --setup to configure access.")
        print("\nKHZR TERMINAL | Groq + Gemini")
        print("Groq is primary. Gemini is automatic backup.")
        print("Type your OOP question. Commands: /help, /clear, /exit\n")
        history = []
        if args.ask:
            print(request_answer(url, token, args.ask, history))
            return 0
        while True:
            try:
                question = input("You > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                return 0
            if question.lower() in {"/exit", "/quit"}:
                print("Bye.")
                return 0
            if question.lower() == "/help":
                print("Paste a C++ OOP question. KHZR returns a complete working solution.")
                print("Commands: /clear  reset conversation history | /exit  quit")
                continue
            if question.lower() == "/clear":
                history.clear()
                print("Chat history cleared.")
                continue
            if not question:
                continue
            try:
                answer = request_answer(url, token, question, history)
                print("\nKHZR > " + answer + "\n")
                history.extend([{"role": "user", "content": question[:2000]}, {"role": "assistant", "content": answer[:2000]}])
                history = history[-8:]
            except ClientError as exc:
                print(f"\n[ERROR] {exc}\n")
    except ClientError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
