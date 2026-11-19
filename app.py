"""Authenticated, stateless KHZR study assistant with provider fallback."""

import hmac
import json
import os
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

app = FastAPI(
    title="KHZR Terminal API",
    version="1.3.0",
    description="Authenticated C++ and OOP study assistant with AI provider fallback.",
    docs_url=None,
    redoc_url=None,
)

SYSTEM_INSTRUCTIONS = (
    "You are KHZR, an expert C++ and OOP lab assistant. "
    "When a student pastes a C++ lab question or programming problem, "
    "provide a COMPLETE, fully-working C++ solution with all necessary includes, "
    "a main() function, and inline comments explaining each OOP concept used. "
    "Format code in a single fenced block. After the code, add a brief explanation. "
    "If the question is conceptual, give a clear, concise explanation with a short C++ snippet. "
    "Never pretend to have executed code or verified a claim if you have not. "
    "Keep answers focused and practical."
)


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content must not be blank")
        return value


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=4000)
    history: list[Turn] = Field(default_factory=list, max_length=8)

    @field_validator("question")
    @classmethod
    def nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class AskResponse(BaseModel):
    answer: str
    model: str


def require_token(
    x_study_token: str | None = Header(default=None, alias="X-Study-Token"),
    authorization: str | None = Header(default=None),
) -> None:
    expected = os.getenv("SERVER_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Server authentication is not configured")
    provided = (x_study_token or "").strip()
    if not provided:
        scheme, _, bearer = (authorization or "").partition(" ")
        if scheme.lower() == "bearer":
            provided = bearer.strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _messages(question: str, history: list[Turn]) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTIONS}]
    messages.extend({"role": turn.role, "content": turn.content} for turn in history)
    messages.append({"role": "user", "content": question})
    return messages


def _groq_answer(question: str, history: list[Turn]) -> AskResponse:
    # Accept both conventional uppercase and the lowercase Vercel variable
    # name the project owner already configured.
    api_key = (os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key") or "").strip()
    if not api_key:
        raise RuntimeError("Groq API key is not configured")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
    payload = {
        "model": model,
        "messages": _messages(question, history),
        "max_completion_tokens": 2048,
        "temperature": 0.2,
    }
    request = Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=25) as response:
        body = json.load(response)
    answer = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("Groq returned no text")
    return AskResponse(answer=answer.strip(), model=f"groq/{model}")


def _gemini_answer(question: str, history: list[Turn]) -> AskResponse:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Gemini API key is not configured")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    contents = []
    for turn in history:
        role = "model" if turn.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": turn.content}]})
    contents.append({"role": "user", "parts": [{"text": question}]})
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTIONS}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 2048},
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=25) as response:
        body = json.load(response)
    answer = "\n".join(
        part.get("text", "")
        for candidate in body.get("candidates", [])
        for part in candidate.get("content", {}).get("parts", [])
        if isinstance(part.get("text"), str)
    ).strip()
    if not answer:
        raise RuntimeError("Gemini returned no text")
    return AskResponse(answer=answer, model=f"gemini/{model}")


def get_answer(question: str, history: list[Turn]) -> AskResponse:
    """Try Groq first, then Gemini. Never expose provider response bodies or keys."""
    groq_key = (os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key") or "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not groq_key and not gemini_key:
        raise HTTPException(status_code=503, detail="No AI provider is configured")

    failures: list[str] = []
    providers = []
    if groq_key:
        providers.append(("Groq", _groq_answer))
    if gemini_key:
        providers.append(("Gemini", _gemini_answer))

    for provider_name, provider in providers:
        try:
            return provider(question, history)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError, RuntimeError) as exc:
            status = f" HTTP {exc.code}" if isinstance(exc, HTTPError) else ""
            print(f"{provider_name} provider failed:{status} ({type(exc).__name__})", flush=True)
            failures.append(f"{provider_name}{status}")

    raise HTTPException(
        status_code=502,
        detail="All configured AI providers failed. Tried: " + ", ".join(failures),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/ask", response_model=AskResponse, dependencies=[Depends(require_token)])
def ask(body: AskRequest) -> AskResponse:
    return get_answer(body.question, body.history)
