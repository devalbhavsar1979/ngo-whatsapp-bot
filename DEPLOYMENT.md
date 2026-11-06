# Deploy to Vercel

This repository is a Flask app that Vercel can run as a Python Function. The
steps below deploy it for testing. **The current conversation and export design
is not reliable for production on Vercel**: sessions are in process memory, and
complaint email/Google Sheets exports run in daemon threads. See
[Production readiness](#production-readiness) before using this for live
complaints.

The deployment supports two answer modes. `IVR` reads only `qna_data.json`. `RAG`
loads a prebuilt FAISS index containing derived chunks and embeddings from approved
remote PDF/website URLs. Original PDFs are downloaded temporarily by `ingest.py`
and are not retained by the application.

## 1. Prepare accounts and credentials

You will need:

- This repository pushed to GitHub.
- A Vercel account with permission to import the repository.
- A Meta developer app with WhatsApp Cloud API configured.
- The WhatsApp **Phone Number ID** and a suitable access token.
- A private verify-token string that you choose. It must match in Vercel and
  Meta.

Optional:

- `GROQ_API_KEY` enables translation in IVR mode and is required for grounded
  answer generation in RAG mode. Without it, IVR text remains untranslated.
- `RESEND_API_KEY` and `ADMIN_EMAIL` enable complaint notification emails.
- `GOOGLE_CREDENTIALS_JSON` enables Google Sheets exports.

Answer-mode settings:

| Variable | Required | Description |
|---|---:|---|
| `ANSWER_MODE` | Yes | `IVR` or `RAG`; missing/invalid values stop startup |
| `IVR_CONFIG_PATH` | IVR | Configurable IVR JSON path; defaults to `ivr_config.json` |
| `RAG_INDEX_PATH` | RAG | Packaged FAISS directory; defaults to `ngo_index` |
| `RAG_EMBEDDING_MODEL` | RAG | Must match the index manifest; defaults to `BAAI/bge-small-en-v1.5` |
| `RAG_EMBEDDING_MODEL_PATH` | RAG on Vercel | Bundled model directory; use `embedding_models/bge-small-en-v1.5` |
| `RAG_LLM_MODEL` | RAG | Groq generation model; defaults to `openai/gpt-oss-120b` |
| `RAG_TOP_K` | No | Retrieved chunks; defaults to `5` |
| `RAG_MIN_SCORE` | No | Minimum relevance score; defaults to `0.35` and should be evaluation-tuned |
| `RAG_MAX_CONTEXT_CHARS` | No | Maximum retrieved context; defaults to `12000` |

`GROQ_API_KEY` is required in RAG mode. `/health` returns HTTP 503 when the RAG
index or Groq client is unavailable.

Vercel should use the deployment-packaged embedding model instead of attempting
to download it during a function cold start:

```dotenv
RAG_EMBEDDING_MODEL_PATH=embedding_models/bge-small-en-v1.5
```

## Build a RAG index from remote sources

1. Copy `rag_sources.example.json` to an administrator-controlled manifest and
   replace its example URLs. Do not accept source URLs from WhatsApp users.
2. Install ingestion dependencies:

   ```powershell
   python -m pip install -r requirements-ingest.txt
   ```

3. Configure and build an immutable versioned index:

   ```powershell
   $env:RAG_SOURCE_MANIFEST = "rag_sources.json"
   $env:RAG_ALLOWED_DOMAINS = "www.example.org,example.org"
   python ingest.py --output ngo_index_2026_11_06
   ```

4. Package that directory with the deployment and set
   `RAG_INDEX_PATH=ngo_index_2026_11_06`. Updating a source requires building a
   new directory and redeploying it.

The source hosts form the default redirect allow-list. `RAG_ALLOWED_DOMAINS` can
set it explicitly. HTTPS is required by default. For an intentionally trusted
plain-HTTP source only, `RAG_ALLOW_HTTP=true` permits HTTP while accepting its
content-integrity risk. `RAG_MAX_SOURCE_BYTES` defaults to 25 MiB per response.

Never commit `.env`, API tokens, or service account credentials.

## 2. Import the project into Vercel

1. In Vercel, select **Add New → Project** and import this GitHub repository.
2. Set the project root to the repository root.
3. Use the default build settings. Do not set a custom build command or output
   directory; Vercel detects the root `app.py` Flask entrypoint and installs
   the Python packages in `requirements.txt`.
4. Add the environment variables in the next section before deploying.
5. Deploy and wait for the build to complete.

Vercel's Python runtime currently supports Python 3.12–3.14. This repository's
`.python-version` selects 3.12 for deployment.

## 3. Add environment variables

In the Vercel project, open **Settings → Environment Variables** and add:

| Name | Required? | Value |
|---|---|---|
| `PHONE_NUMBER_ID` | Yes | Phone Number ID from Meta WhatsApp API setup |
| `ACCESS_TOKEN` | Yes | Meta token that can send WhatsApp messages and retrieve media |
| `VERIFY_TOKEN` | Yes | A secret string you generate; use the exact same value in Meta's webhook setup |
| `ANSWER_MODE` | Yes | Set to `IVR` or `RAG` |
| `GROQ_API_KEY` | Optional | Groq API key |
| `RESEND_API_KEY` | Optional | Resend API key |
| `ADMIN_EMAIL` | Optional | Complaint notification recipient |
| `GOOGLE_CREDENTIALS_JSON` | Optional | Full Google service-account JSON value |

Set the required variables for **Production**. Add them to Preview only if you
intend to test the Meta webhook on preview deployments. After changing
environment variables, redeploy so the new values are applied.

`VERIFY_TOKEN` is not issued by Meta. Generate a random secret yourself (for
example, with a password manager or by running
`[guid]::NewGuid().ToString('N')` in PowerShell), save it as `VERIFY_TOKEN` in
Vercel, and enter that exact same string as the webhook's **Verify token** in
Meta. Do not use your Meta `ACCESS_TOKEN` for this.
// cfc96b9547aa4c32adb951752dd98d83


For Google Sheets, create a spreadsheet named exactly `NGO Chatbot Complaints`
and share it with the service account's `client_email` as an editor. The app
creates a header row if the first row is empty.

For email, set both Resend variables. The current implementation sends from
`NGO Bot <onboarding@resend.dev>`; check Resend's sender verification rules and
update the sender in `email_service.py` if you need to use your own domain.

## 4. Check the deployment

Open the production deployment URL:

- `/` should return JSON with `"status": "running"`.
- `/health` should return JSON with `"status": "healthy"`.
- `/static/cerc_logo.png` should display the greeting image served from
  `public/static/cerc_logo.png`.

If these URLs work, the Flask function and static asset are deployed.

## 5. Connect Meta WhatsApp webhooks

For the full step-by-step Meta app and phone-number setup, see
[META_WHATSAPP_SETUP.md](META_WHATSAPP_SETUP.md).

1. In the Meta developer app, open the WhatsApp product's **Configuration**.
2. Enter the Vercel production URL ending in `/webhook` as the **Callback URL**:

   ```text
   https://<your-project>.vercel.app/webhook
   ```

3. Enter the exact `VERIFY_TOKEN` value you saved in Vercel.
4. Select **Verify and Save**.
5. Subscribe the WhatsApp Business Account to the **messages** webhook field.
   The app also uses outgoing status notifications when Meta sends them.
6. If using the Meta test number in development mode, add and verify the phone
   you will test from as a **To** recipient in **WhatsApp → API Setup**. See
   the [Meta WhatsApp setup guide](META_WHATSAPP_SETUP.md#2-try-the-test-number)
   for the click-by-click steps.

Meta verification calls `GET /webhook`; incoming messages use `POST /webhook`.
If verification fails, confirm the URL, deployment status, and verify-token
match.

## 6. Send a test message

1. Send `hi` to the configured WhatsApp number.
2. Confirm you receive the logo greeting and language picker.
3. Select a language and try the FAQ menus.
4. Submit a test complaint.
5. Inspect Vercel **Logs** for request errors. If optional integrations are
   enabled, check their logs/results too.

Vercel functions are request-driven and can be invoked in different instances.
The deployment may look healthy while a multi-message conversation loses its
state. See the production notes below.

## Production readiness

Do not treat the default deployment as a reliable complaint intake system until
these application changes are made:

1. **Persist sessions and deduplication externally.** `state_machine.py`,
   `SEEN_MESSAGES`, and pending greeting prompts in `app.py` are in-memory.
   Vercel may handle two messages from the same person in different instances,
   and instances can be restarted. Use a shared persistent store such as Redis
   or a database, with expiration and atomic message deduplication.
2. **Replace daemon-thread exports with durable work.** On confirmation, the
   app starts a daemon thread for email and Sheets work. A serverless function
   may stop or freeze after returning the webhook response, so this work is not
   guaranteed to finish. Use a durable queue/background-work service, or
   process the work synchronously with a carefully chosen response strategy.
3. **Test Meta retry behavior.** The current in-memory duplicate protection
   lasts only 60 seconds and is not shared across instances. Persist processed
   message IDs before relying on it to prevent duplicate complaint processing.

Vercel is suitable for trying the stateless endpoints and webhook verification.
For live complaint filing, address the above reliability requirements first.

## Troubleshooting

- **Build fails:** check the Vercel build logs and confirm `.python-version` is
  `3.12`, `requirements.txt` is in the project root, and the repository is
  selected as the project root.
- **`/health` fails:** open the function logs for import or startup errors.
- **Meta verification fails:** check `/webhook`, `VERIFY_TOKEN`, and that the
  deployment is available publicly over HTTPS.
- **Bot cannot send messages:** confirm `PHONE_NUMBER_ID` and `ACCESS_TOKEN`
  belong to the same WhatsApp setup and that the token has not expired.
- **Image greeting is broken:** confirm `/static/cerc_logo.png` is available;
  the Vercel asset is `public/static/cerc_logo.png`.
- **Email or Sheets data is missing:** check the related Vercel environment
  variables and function logs. Daemon-thread work is not guaranteed to finish
  on Vercel; use a durable job queue for production.

## Official Vercel references

- [Deploy a Flask app](https://vercel.com/docs/frameworks/backend/flask)
- [Python runtime and entrypoints](https://vercel.com/docs/functions/runtimes/python)
- [Set the Python version](https://vercel.com/docs/functions/runtimes/python/python-version)
- [Vercel Function limits](https://vercel.com/docs/functions/limitations)
