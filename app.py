"""Authenticated, stateless Gemini-powered study assistant."""

import hmac
import json
import os
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator


app = FastAPI(
    title="Terminal Study Assistant",
    version="1.1.2",
    description="A small, authenticated study assistant API.",
    docs_url=None,
    redoc_url=None,
)

SYSTEM_INSTRUCTIONS = (
    "You are a concise, patient study tutor. Help students understand concepts "
    "using clear explanations, short worked examples, and debugging tips. "
    "For live graded assessments, coach the student through the concepts "
    "instead of giving direct answers to assessment questions. "
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
    """Check the server token. Prefer the app-specific header."""
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


def get_answer(question: str, history: list[Turn]) -> AskResponse:
    """Generate an answer using the Gemini API."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini API is not configured")

    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
    contents = []
    for turn in history:
        role = "model" if turn.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": turn.content}]})
    contents.append({"role": "user", "parts": [{"text": question}]})

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTIONS}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 600},
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

    try:
        with urlopen(request, timeout=25) as response:
            body = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Gemini provider request failed") from exc

    answer = "\n".join(
        part.get("text", "")
        for candidate in body.get("candidates", [])
        for part in candidate.get("content", {}).get("parts", [])
        if isinstance(part.get("text"), str)
    ).strip()
    if not answer:
        raise HTTPException(status_code=502, detail="Gemini returned no text")

    return AskResponse(answer=answer, model=model)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/v1/ask",
    response_model=AskResponse,
    dependencies=[Depends(require_token)],
)
def ask(body: AskRequest) -> AskResponse:
    return get_answer(body.question, body.history)
