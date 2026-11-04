# NGO WhatsApp Bot

Flask webhook application for the Meta WhatsApp Cloud API. It supports multilingual
chat, complaint intake, FAQ responses from `qna_data.json`, optional Groq-powered
category suggestions and translation, and optional complaint notifications through
Resend and Google Sheets.

## Deploy to Vercel

See [DEPLOYMENT.md](DEPLOYMENT.md) for the Vercel setup, Meta webhook configuration,
environment variables, smoke tests, and production limitations.

For setting up the Meta app, WhatsApp number, access token, and webhook itself,
see the separate [Meta WhatsApp setup guide](META_WHATSAPP_SETUP.md).

## Run locally

Requires Python 3.12 (the version in `.python-version`), a configured `.env` file,
and the values described in [DEPLOYMENT.md](DEPLOYMENT.md).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

The local server listens on port 5000. To receive Meta webhooks during development,
expose it through an HTTPS tunnel and configure the tunnel URL ending in `/webhook`
in the Meta app. PDF ingestion is separate from the live app; to run `ingest.py`,
install its additional dependencies with `python -m pip install -r requirements-ingest.txt`.

## Project files

- `app.py`: Flask routes, WhatsApp webhook handling, and conversation flow
- `state_machine.py`: in-memory conversation/session state
- `complaint_data.py` and `qna_data.json`: FAQ/category data
- `email_service.py`: optional Resend notifications and WhatsApp attachment downloads
- `google_sheets.py`: optional Google Sheets complaint export
- `static/cerc_logo.png`: greeting image served to WhatsApp
