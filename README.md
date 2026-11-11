# Terminal Study Assistant

A small AI study tutor with a hosted FastAPI server and a dependency-free Python terminal client. For personal study and other authorized environments.

## What you get

- `app.py`: FastAPI service, authenticated `/v1/ask` endpoint, `/health` check
- `client.py`: Python 3 terminal chat with `/clear`, `/exit` and one-shot `--ask`
- OpenAI Responses API over HTTPS on the server, with the provider API key never sent to the client
- Limited chat history, input validation, error handling, tests and CI
- Vercel-compatible FastAPI entrypoint

The terminal client **requires permitted HTTPS access** to the deployed server. It does not bypass firewalls, authentication, device policy, or other network access restrictions. Do not use it during assessments unless explicitly permitted.

## 1. Run locally

Install Python 3.12+ and run in the project folder:

```bash
python -m venv .venv
```

Activate the virtual environment:

- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Then:

```bash
python -m pip install -r requirements.txt
```

Set environment variables in the server terminal. Generate a strong server token:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

PowerShell:

```powershell
$env:OPENAI_API_KEY="YOUR_REAL_OPENAI_KEY"
$env:SERVER_TOKEN="PASTE_RANDOM_TOKEN"
$env:OPENAI_MODEL="gpt-4.1-mini"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

macOS/Linux:

```bash
export OPENAI_API_KEY="YOUR_REAL_OPENAI_KEY"
export SERVER_TOKEN="PASTE_RANDOM_TOKEN"
export OPENAI_MODEL="gpt-4.1-mini"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open a **second** terminal:

PowerShell:

```powershell
$env:TUTOR_TOKEN="PASTE_RANDOM_TOKEN"
python client.py --url http://127.0.0.1:8000
```

macOS/Linux:

```bash
export TUTOR_TOKEN="PASTE_RANDOM_TOKEN"
python client.py --url http://127.0.0.1:8000
```

Example question: `Explain C++ constructors with a simple example.`

## 2. Deploy on Vercel

Vercel supports zero-config FastAPI apps that expose a `FastAPI` instance named `app` in `app.py`. No custom rewrite file or keepalive is required.

1. Push this directory to your own **private** Git repository.
2. In Vercel, create a new project by importing that repo. Choose the default FastAPI detection. Leave build/output overrides empty.
3. Add the following project **Environment Variables** in Vercel settings: `OPENAI_API_KEY`, `SERVER_TOKEN`, and optionally `OPENAI_MODEL` (default `gpt-4.1-mini`).
4. Deploy. Confirm `https://YOUR-DEPLOYMENT/health` returns `{"status":"ok"}`.
5. In a permitted external network, set `TUTOR_TOKEN` to the server token and run:

```bash
python client.py --url https://YOUR-DEPLOYMENT
```

Or ask a single question:

```bash
python client.py --url https://YOUR-DEPLOYMENT --ask "Explain polymorphism"
```

Avoid placing either secret in the repository or embedding it into a distributed client. Be aware the server token allows its holder to spend your provider API allowance. Rotate it if shared or leaked. Vercel deployment is not an assurance that a restricted network will allow requests to it.

## 3. Run tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use a mocked AI provider and require no provider key or network access.

## Limitations

- Hosted model API usage may cost money and requires its own provider account.
- A `SERVER_TOKEN` grants access to whoever knows it. Do not share it publicly. Requests are authenticated, but there is no persistent user database, centralized quota enforcement, or multi-tenant billing. Set provider-side spending limits for personal use.
- Requests are synchronous and capped at 600 output tokens, with up to eight short previous chat turns.
- An external connection must be authorized and reachable for the remote version to function. For disconnected study practice, use your local notes or an offline learning tool instead.

## KHZR Vercel deployment (October 25, 2026)

A separate Vercel project named `terminal-study-assistant-khzr` has been created under the KHZR team and a first build was reported `READY` at:

`https://terminal-study-assistant-khzr.vercel.app`

The local Windows launcher `run_windows.bat` uses this address by default. The server access token was configured on Vercel, but is deliberately stored **outside** this project archive in the separate file `terminal-study-assistant-access.txt`. On Windows you can double-click `run_windows.bat` and enter the token when asked. Python 3 is required on the computer.

**Live limitations:** The OpenAI provider API key has not been configured. Until you add `OPENAI_API_KEY` in this project's Vercel environment settings and redeploy, `/v1/ask` returns 503. The project also inherited **Vercel Authentication** deployment protection (`all_except_custom_domains`), so an unauthenticated terminal client cannot access it until you configure deployment access appropriately for this project. The deployed build has not been verified with a real external HTTP request because the test environment lacks network access. No claim is made that it works over a university-managed restricted network.

The app itself requires authorized HTTPS connectivity. It does not change firewall rules, bypass university authentication, or offer a method for use in restricted examinations.
