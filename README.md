# Terminal Study Assistant

A terminal-based AI study tutor. The Python terminal client talks to an authenticated FastAPI server, and the server sends questions to Google's Gemini Developer API. The Gemini API key stays on the server.

## Features

- Terminal chat with conversation history
- `/clear`, `/help`, and `/exit` commands
- One-question mode with `--ask`
- FastAPI server with bearer-token authentication
- Gemini model selection through `GEMINI_MODEL`
- Input validation and automated tests

Use the service only on networks and in situations where access is permitted. Do not use it during exams or graded assessments unless your instructor explicitly allows it.

## 1. Run locally on Windows

Install Python 3.12 or newer. Open PowerShell in this project folder.

Create and activate a virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set the server configuration. Get a Gemini API key from Google AI Studio. Generate a private server token:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

In the same PowerShell window, set the values and start the API:

```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
$env:GEMINI_MODEL="gemini-3.8-flash"
$env:SERVER_TOKEN="PASTE_YOUR_RANDOM_TOKEN"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Keep that window open. Open a second PowerShell window in the same project folder:

```powershell
.\.venv\Scripts\Activate.ps1
$env:TUTOR_TOKEN="PASTE_THE_SAME_RANDOM_TOKEN"
python client.py --url http://127.0.0.1:8000
```

Ask a question in the terminal. Type `/exit` to quit.

To ask one question without starting a chat:

```powershell
python client.py --url http://127.0.0.1:8000 --ask "Explain C++ constructors"
```

## 2. Deploy using the existing Vercel project

The existing Vercel project is named `terminal-study-assistant-khzr`. Do not create a second project.

1. Open the Vercel dashboard and select the existing `terminal-study-assistant-khzr` project.
2. Open Settings, then Git. Connect the GitHub repository `every1hatestaha-png/terminal-study-assistant` if it is not connected already.
3. In Settings, open Environment Variables. Confirm these variables exist for the Production environment:
   - `GEMINI_API_KEY`: your Gemini API key
   - `GEMINI_MODEL`: `gemini-3.8-flash`
   - `SERVER_TOKEN`: your private random server token
4. Save any missing variables, then redeploy the latest `main` commit.
5. Open `https://terminal-study-assistant-khzr.vercel.app/health`. A working public health endpoint returns `{"status":"ok"}`.

If Vercel Deployment Protection blocks the terminal client, the deployment owner must configure access for this project. Do not publish or share the server token. Do not turn off organization-wide security settings.

After the deployment is accessible, run the client from PowerShell:

```powershell
$env:TUTOR_TOKEN="PASTE_THE_SAME_SERVER_TOKEN"
python client.py --url https://terminal-study-assistant-khzr.vercel.app
```

One-question mode:

```powershell
python client.py --url https://terminal-study-assistant-khzr.vercel.app --ask "Explain polymorphism"
```

## 3. Windows launcher

You can also run `run_windows.bat`. It starts the terminal client using the configured Vercel URL and asks for the server token if `TUTOR_TOKEN` is not set.

## 4. Run tests

Install development dependencies and run the full test suite:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The tests mock the Gemini HTTP response. They verify application behavior without spending API credits, but they do not replace a live API test.

## Configuration

| Variable | Used by | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | Server | Google Gemini API key |
| `GEMINI_MODEL` | Server | Gemini model ID, defaults to `gemini-3.8-flash` |
| `SERVER_TOKEN` | Server | Protects the API endpoint |
| `TUTOR_URL` | Client | Optional default server URL |
| `TUTOR_TOKEN` | Client | Bearer token matching `SERVER_TOKEN` |

Never commit `.env`, API keys, or server tokens. The terminal client does not need the Gemini API key.

## Limitations

- Gemini API access requires a Google AI Studio API key and may be subject to quotas or billing.
- Anyone with the server token can use the hosted API and consume its Gemini quota. Keep the token private and rotate it if exposed.
- The service keeps conversation history in the terminal client, not in a user database.
- The server allows up to eight prior turns and limits generated output to 600 tokens.
- A successful Vercel build does not prove that the live API key, deployment access settings, or external network connection work. Test the health endpoint and then send a real question.
