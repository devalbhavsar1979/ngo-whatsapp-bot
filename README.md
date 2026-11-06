# NGO WhatsApp Bot

Flask webhook application for the Meta WhatsApp Cloud API. It supports multilingual
chat, complaint intake, strict predefined FAQ responses from `qna_data.json`, and a
configurable RAG question-answer mode over approved remote PDF/website sources.
Complaint notifications can optionally be sent through Resend and Google Sheets.

Set `ANSWER_MODE=IVR` for predefined Product/Service -> Category -> FAQ navigation,
or `ANSWER_MODE=RAG` for natural-language answers grounded in a prebuilt FAISS index.
The variable is required and an invalid or missing value stops application startup.
See [DEPLOYMENT.md](DEPLOYMENT.md) for index-building and environment configuration.

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
- `complaint_data.py` and `qna_data.json`: strict IVR FAQ/category data
- `answer_config.py` and `rag_service.py`: mode configuration and grounded RAG answers
- `ingest.py`: controlled remote PDF/website ingestion into a packaged FAISS index
- `rag_sources.example.json`: example administrator-controlled source manifest
- `email_service.py`: optional Resend notifications and WhatsApp attachment downloads
- `google_sheets.py`: optional Google Sheets complaint export
- `static/cerc_logo.png`: greeting image served to WhatsApp
