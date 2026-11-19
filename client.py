"""KHZR Terminal client with one-time local setup and persistent settings."""
import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

DEFAULT_URL = "https://terminal-study-assistant-khzr.vercel.app"
APP_DIR = Path(os.getenv("APPDATA") or Path.home()) / "KHZR"
CONFIG = APP_DIR / "config.json"

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
    CONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG, 0o600)
    except OSError:
        pass

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
    print("This saves your private access token on this Windows account.")
    url = input(f"Server URL [{config.get('url', DEFAULT_URL)}]: ").strip() or config.get("url", DEFAULT_URL)
    url = validate_url(url)
    token = getpass.getpass("Server access token: ").strip()
    if not token:
        raise ClientError("A non-empty token is required.")
    config.update({"url": url, "token": token})
    save_config(config)
    print(f"Setup saved to {CONFIG}")
    print("Next time, open CMD anywhere and type: khzr")
    return config

def request_answer(url, token, question, history):
    payload = json.dumps({"question": question, "history": history}).encode("utf-8")
    request = Request(url + "/v1/ask", data=payload, method="POST", headers={
        "Content-Type": "application/json", "X-Study-Token": token, "Accept": "application/json"
    })
    try:
        with urlopen(request, timeout=45) as response:
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
            502: "Gemini did not respond. Check the server logs and API key.",
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
    return answer

def run():
    parser = argparse.ArgumentParser(prog="khzr", description="KHZR Terminal AI assistant")
    parser.add_argument("--setup", action="store_true", help="Save or replace server settings")
    parser.add_argument("--ask", help="Ask one question and exit")
    args = parser.parse_args()
    config = load_config()
    try:
        if args.setup or not config.get("token"):
            config = setup(config)
        url = validate_url(config.get("url", DEFAULT_URL))
        token = str(config.get("token", "")).strip()
        if not token:
            raise ClientError("Run khzr --setup to configure access.")
        print("\nKHZR TERMINAL | Gemini AI")
        print("Type your question. Commands: /help, /clear, /exit\n")
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
                print("Paste a practice question. Use /clear to reset context and /exit to quit.")
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
