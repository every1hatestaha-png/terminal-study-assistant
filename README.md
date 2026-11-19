# KHZR Terminal

A Windows terminal assistant for C++ and OOP practice. The hosted FastAPI server uses Groq first and automatically falls back to Gemini. Provider API keys stay on the server.

## Features

- Groq primary provider, Gemini automatic fallback
- Terminal chat with conversation history
- `/clear`, `/help`, and `/exit` commands
- One-question mode with `--ask`
- Bearer-token authentication
- Server token stored in Windows Credential Manager, not plaintext config
- Input validation and automated tests

Use the service only where AI assistance is permitted by your instructor.

## Install on a Windows computer

1. Download the repository ZIP from GitHub and extract it.
2. Run `install_khzr.bat`.
3. Enter the server URL if you want to change the default.
4. Enter the private server access token once on that Windows account. KHZR stores it in Windows Credential Manager.
5. Close the installer, open a new CMD window, and type:

```cmd
khzr
```

On that same Windows account, you should not need to enter the token again. A new computer needs its own one-time setup. If you need to replace credentials, run `khzr --setup`.

Python 3 is required. The installer installs the `keyring` package and adds the KHZR command directory to the user PATH.

## Server deployment

Existing Vercel project: `terminal-study-assistant-khzr`.

Configure these Production environment variables in Vercel:

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` or `groq_api_key` | Groq API key. Groq is tried first. |
| `GROQ_MODEL` | Optional Groq model. Defaults to `openai/gpt-oss-120b`. |
| `GEMINI_API_KEY` | Optional Gemini backup key. |
| `GEMINI_MODEL` | Optional Gemini model. Defaults to `gemini-2.5-flash`. |
| `SERVER_TOKEN` | Private token required by the terminal client. |

After changing environment variables, redeploy the project. Never commit API keys or server tokens.

## Local development

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
$env:GROQ_API_KEY="YOUR_GROQ_KEY"
$env:GEMINI_API_KEY="YOUR_GEMINI_KEY"
$env:SERVER_TOKEN="YOUR_RANDOM_SERVER_TOKEN"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests mock provider responses and do not consume API credits. A passing deployment build does not prove that the live API keys work. Test the deployed terminal with a real question.

## Security

- Never put provider API keys in the terminal client.
- Never commit `.env`, provider keys, or server tokens.
- The server token is stored using the operating system credential store on Windows.
- Anyone who has the server token can access the hosted API, so keep it private and rotate it if exposed.
