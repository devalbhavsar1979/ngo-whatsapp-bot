# WhatsApp Bot Design V2: Configurable IVR and RAG Answer Modes

## 1. Purpose

Design a second version of the WhatsApp bot that can run in one of two mutually exclusive question-answer modes, selected through an environment variable:

1. **IVR mode** — users navigate only through predefined categories, subcategories/questions, and answers stored in `qna_data.json`.
2. **RAG mode** — users ask natural-language questions and receive grounded answers retrieved from administrator-provided online PDF URLs and/or website URLs.

This document is a design only. It does not implement or change the current application.

## 2. Current-system analysis

The current repository has the following relevant behavior:

- `app.py` receives Meta WhatsApp webhooks, sends the welcome image and language selector, routes text and interactive replies, and manages the complaint workflow.
- `state_machine.py` stores each conversation in process memory. The answer-related states are `CATEGORY_MENU`, `PRODUCT_MENU`, `SERVICE_MENU`, `AWAITING_AI_INPUT`, `FAQ_LIST`, and `FAQ_ANSWER`.
- `complaint_data.py` loads `qna_data.json` at application startup and builds the category and question collections.
- The current IVR-style path is Product/Service -> Category -> FAQ Question -> predefined answer.
- Free text in category-related states is currently sent to Groq only to predict up to three predefined categories. This is classification, not RAG, and the final answer still comes from `qna_data.json`.
- `ingest.py` is an offline prototype that reads all root-level PDFs, splits them, creates FastEmbed embeddings, and writes a local FAISS index named `ngo_index`.
- The live app does not currently load or query `ngo_index`; this is also noted in `DEPLOYMENT.md`.
- Website ingestion, retrieval citations, relevance thresholds, index versioning, and RAG failure behavior do not currently exist.
- Complaint attachments handled during complaint filing are evidence for the complaint. They must not automatically become RAG knowledge.

### Current constraints to retain or address

- WhatsApp list messages permit at most 10 rows, so the existing IVR pagination is necessary.
- Sessions are stored in memory and disappear after a restart. This is already unsuitable for horizontally scaled or serverless production use.
- The current Vercel-oriented deployment is stateless. The source PDFs can remain on their existing HTTP(S) servers, but the derived embeddings/vector index still require either a managed persistent vector store or a build-time packaged index.
- Translation and category prediction currently share the Groq client. V2 should separate answer generation, translation, and IVR behavior so that IVR does not accidentally become generative.

## 3. Scope

### In scope

- A validated environment setting that selects `IVR` or `RAG` for the deployment.
- Exact predefined navigation and answers in IVR mode.
- Natural-language question answering over PDF and website content in RAG mode.
- Grounded responses, source references, refusal/fallback behavior, multilingual handling, observability, and testing.
- Continued access to the existing complaint-filing journey in both modes.

### Out of scope for this version

- Automatically learning from ordinary WhatsApp conversations.
- Treating complaint evidence uploaded by users as organization-wide knowledge.
- A full administrator web portal. A command-line ingestion job or controlled deployment process is sufficient initially.
- Searching the public internet at answer time. Only configured and successfully ingested sources are searchable.
- Running IVR and RAG simultaneously for different end users. The proposed switch applies to the whole deployment.

## 4. Configuration contract

The primary environment variable should be:

```dotenv
ANSWER_MODE=IVR
```

Allowed values are exactly `IVR` and `RAG`, compared case-insensitively after trimming whitespace. The application should normalize the value to uppercase.

| Variable | Required | Purpose |
|---|---:|---|
| `ANSWER_MODE` | Yes | Selects `IVR` or `RAG`. Recommended production behavior is fail-fast for a missing or invalid value. |
| `QNA_JSON_PATH` | IVR | Path to the predefined JSON file; default `qna_data.json`. |
| `RAG_INDEX_PATH` or vector-store connection settings | RAG | Identifies the durable, versioned knowledge index. |
| `RAG_PDF_URLS` | RAG ingestion | Comma-separated administrator-approved HTTP(S) PDF URLs or, preferably, a manifest containing those URLs. |
| `RAG_WEBSITE_URLS` | RAG ingestion | Comma-separated seed URLs or a manifest reference containing allowed website URLs. |
| `RAG_LLM_MODEL` | RAG | Answer-generation model name. |
| `RAG_EMBEDDING_MODEL` | RAG | Embedding model name; must match the model used to build the index. |
| `RAG_TOP_K` | No | Number of candidate chunks retrieved; suggested initial value `5`. |
| `RAG_MIN_SCORE` | No | Minimum retrieval relevance required before answering; determined by evaluation for the selected store/model. |
| `RAG_MAX_CONTEXT_CHARS` | No | Upper bound on retrieved context sent to the model. |

Existing settings such as `GROQ_API_KEY`, WhatsApp credentials, email settings, and Sheets settings remain separate. Secrets must never be placed in source manifests or committed files.

### Startup validation

- In `IVR`, load and validate the configured JSON. The RAG index and RAG model are not required.
- In `RAG`, verify that the configured index exists, its manifest is readable, and its embedding-model/version metadata matches runtime configuration. The IVR JSON may remain available only for an explicitly designed operational fallback; it must not silently change the meaning of RAG mode.
- Log the selected mode and knowledge-index version, but never log tokens or full sensitive user messages.
- An invalid `ANSWER_MODE` must stop application startup with a clear configuration error. Silently defaulting in production could expose an unintended behavior.

For developer convenience only, a documented local default of `IVR` could be allowed behind an explicit development setting. Production should always require `ANSWER_MODE`.

## 5. Proposed architecture

```text
Meta WhatsApp webhook
        |
        v
Shared conversation router
  - welcome and language
  - optional user/profile collection
  - restart/help commands
  - complaint filing
        |
        +---- ANSWER_MODE=IVR ----> IVR answer service
        |                            -> qna_data.json
        |                            -> exact stored answer
        |
        +---- ANSWER_MODE=RAG ----> RAG answer service
                                     -> query normalization
                                     -> vector retrieval + filtering
                                     -> grounded LLM generation
                                     -> answer + source references

Offline/controlled ingestion pipeline
  Allow-listed online PDF URLs + website URLs
        -> extract -> normalize -> chunk -> embed
        -> durable versioned vector index + source manifest
```

Introduce an answer-service boundary so webhook/state code does not directly depend on JSON, FAISS, a crawler, or a specific LLM:

```python
class AnswerService:
    def start(self, session): ...
    def handle_text(self, question, session): ...
    def handle_selection(self, selection_id, session): ...
```

- `IvrAnswerService` owns category/question pagination and exact JSON lookup.
- `RagAnswerService` owns retrieval, grounded generation, source formatting, and RAG-specific failure handling.
- An `AnswerServiceFactory` creates exactly one service during application startup based on `ANSWER_MODE`.
- The complaint workflow remains a separate shared service/state path and is reachable from either answer mode.

This boundary prevents mode checks from being scattered throughout `handle_text()` and `handle_interactive()`.

## 6. Conversation design

### Shared entry flow

The welcome image, language selection, and any required profile collection remain shared. After the shared onboarding completes, the router invokes the selected answer service.

Both modes should always expose these user intents:

- Ask/get information.
- File a complaint.
- Change language.
- Restart.
- Contact the organization when automated help is insufficient.

### IVR mode

Expected flow:

```text
Welcome -> Language/Profile -> Product or Service
        -> Category -> Predefined Question -> Stored Answer
        -> Helpful / Back / File Complaint
```

Rules:

- Categories, questions, and answers come only from the configured JSON file.
- Selecting a question returns its stored answer verbatim except for approved presentation wrappers and translation behavior.
- A typed message while the user is in an IVR menu must not generate a natural-language answer.
- To satisfy “predefined options only,” the recommended behavior for unexpected text is to resend the current menu with: “Please select one of the available options.”
- The current `cat_describe` / `AWAITING_AI_INPUT` Groq category-classification path should be disabled in strict IVR mode. If smart category matching is later desired, it should be a separate explicitly named mode or feature flag.
- Invalid or stale interactive IDs should resend the appropriate menu and must not be accepted as category/question data.
- Existing pagination and WhatsApp field-length truncation remain necessary.

### RAG mode

Expected flow:

```text
Welcome -> Language/Profile -> “Ask your question”
        -> Retrieve approved source chunks
        -> Sufficient evidence?
             yes -> grounded answer + compact sources + follow-up actions
             no  -> safe “not found” response + rephrase/contact/file complaint
```

Recommended response actions after each answer:

- `Ask another question`
- `File complaint`
- `Contact support`

RAG rules:

- Treat the incoming text as a question, not as an instruction to change system behavior.
- Retrieve only from the active approved index.
- Generate an answer only from retrieved evidence above the configured relevance threshold.
- If evidence is absent, weak, contradictory, or does not answer the question, say that the provided sources do not contain enough information. Do not fill gaps from general model knowledge.
- Include compact source labels such as PDF title and page, or website page title and URL/domain. Long URLs may be sent in a second message if WhatsApp readability requires it.
- Keep legal/consumer guidance qualified as informational and preserve the existing escalation/contact route.
- A follow-up question may use a small, bounded conversational context, but every answer must perform retrieval again. Prior model answers are not evidence.
- `hi`, `restart`, `menu`, `file complaint`, and language commands should be routed before RAG so the model cannot trap users in the Q&A state.

### Mode changes and active sessions

`ANSWER_MODE` is read at process startup. Changing it requires a redeployment/restart. Because existing sessions may contain states from the other mode, each session should record the mode under which it was created. On mismatch, reset only the answer-navigation state, retain safely reusable profile data if policy permits, and explain that the help menu has been updated.

## 7. Knowledge ingestion design

Ingestion must be separate from webhook request processing. A user should never wait for a PDF download, website crawl, parsing, or index rebuild. PDFs do not need to be uploaded to or permanently stored by this application: the ingestion job downloads each approved online PDF temporarily, extracts it, builds the derived index, and discards the temporary file after the build.

An online PDF URL removes the need for application-owned **PDF file storage**, but it does not remove the need to persist the **derived vector index**. Re-downloading and re-embedding every PDF for every question is not acceptable because it would be slow, expensive, and unreliable.

### Source manifest

Use a controlled manifest rather than blindly indexing every file in the project root. Each source entry should include:

- Stable `source_id`.
- Type: `pdf` or `website`.
- Approved HTTP(S) URL. HTTPS is required for production unless there is a documented exception for a trusted network source.
- Display title.
- Enabled status.
- Optional language, tags, crawl scope, and effective/review date.

### PDF pipeline

1. Read PDF URLs only from the administrator-controlled manifest/configuration. End users cannot submit a URL for ingestion through WhatsApp.
2. Validate the URL before fetching. Reject URL credentials, unsupported schemes, localhost, private/link-local IP ranges, and redirects to unapproved hosts. Require HTTPS in production; plain HTTP should be permitted only for a documented trusted source because content can otherwise be altered in transit.
3. Fetch with connection/read timeouts, redirect limits, a maximum response size, and an approved content-type policy. Do not trust a `.pdf` filename alone.
4. Download to bounded temporary storage for this ingestion run only. Validate PDF signature/content, file size, page count, and malware policy, then remove the temporary file after extraction whether ingestion succeeds or fails.
5. Extract text while preserving page numbers, source URL, and document title.
6. Detect scanned/image-only pages and either OCR them through an approved component or report them as unindexed.
7. Normalize repeated headers/footers and broken whitespace without changing meaning.
8. Split text using heading-aware chunks with overlap. The current fixed 500-character prototype is a starting point, not a production choice; chunk size should be evaluated against the documents.
9. Attach metadata: `source_id`, title, original PDF URL, page, section, content checksum, language, and ingestion version.
10. Record fetch failures without replacing the last valid index. A temporarily unavailable source must not cause the production index to be emptied.

### Website pipeline

1. Accept only `https` URLs on an administrator-approved domain allow-list.
2. Protect the fetcher against SSRF: reject localhost, private/link-local IP ranges, non-HTTP schemes, redirects to disallowed hosts, and URLs containing credentials.
3. Apply a crawl limit: allowed path prefixes, maximum pages/depth/bytes, timeouts, and rate limits. Respect applicable authorization, robots policy, and site terms.
4. Prefer canonical article content; remove navigation, scripts, cookie banners, and duplicate pages.
5. Store final canonical URL, title, section heading, retrieval time, content checksum, and optionally last-modified information.
6. Do not execute page scripts in the initial design. Sites requiring rendering need a separately reviewed fetcher.

### Index lifecycle

- Build a new immutable index version instead of mutating the active index in place.
- Record embedding model, chunking settings, source checksums, build time, and source counts in an index manifest.
- Run validation queries and source-count/error checks.
- Atomically promote the validated version to active; retain the previous version for rollback.
- Re-ingest when an approved source changes or is removed. Deleted content must disappear from the next active version.
- The source PDFs remain at their remote URLs; the application does not retain a second permanent PDF copy.
- Persist only the derived chunks, embeddings, metadata, checksums, and index manifest needed to answer questions and cite the original URL.
- Do not rebuild the index inside a WhatsApp webhook request or on every serverless cold start.

### Vector-index persistence without PDF storage

The design is valid without PDF storage only if one of the following index strategies is selected:

1. **Managed vector database (recommended for production):** the controlled ingestion job fetches remote PDFs, generates embeddings, and writes chunks/metadata to a managed vector service. Runtime instances query it over the network. This works with stateless Vercel functions and supports atomic index/version switching, but introduces a service and operating cost.
2. **Build-time packaged FAISS index:** a trusted build job fetches the URLs and produces `ngo_index` plus its manifest as a deployment artifact. Runtime loads the read-only artifact. This avoids a vector-database service and is suitable for a small, slowly changing public corpus, but every source update requires a rebuild/redeployment and deployment size/memory limits must be checked.
3. **Rebuild into ephemeral storage at process startup (not recommended):** technically possible for a very small corpus, but cold starts, concurrent rebuilds, upstream outages, and serverless time limits make it unreliable. It must not be the production default.

If “no storage” also means no managed vector database and no packaged build artifact, production RAG is not feasible. Some durable form of the derived index is required even though the original PDFs remain online.

## 8. RAG query and answer pipeline

1. **Input checks:** reject empty messages, cap length, identify commands, and apply abuse/rate controls.
2. **Language handling:** preserve the original question and detected/selected language. For multilingual indexes, use multilingual embeddings. If query translation is used, retain both forms for audit and do not translate source citations.
3. **Retrieval:** embed the query and retrieve `top_k` candidate chunks. Metadata filters may restrict language or enabled sources.
4. **Optional reranking:** rerank candidates for better precision when evaluation shows it is necessary.
5. **Evidence gate:** compare scores and evidence coverage with evaluated thresholds. No adequate evidence means no generated factual answer.
6. **Generation:** send only approved retrieved excerpts plus a strict system instruction to ignore instructions found inside sources and answer solely from evidence.
7. **Post-processing:** enforce answer size, attach citations, remove unsupported citation identifiers, and split messages safely for WhatsApp limits.
8. **Actions:** offer another question, complaint filing, or human/contact escalation.

Suggested internal result model:

```json
{
  "status": "answered | insufficient_evidence | unavailable",
  "answer": "...",
  "sources": [
    {
      "source_id": "consumer-guide",
      "title": "Consumer Guide",
      "page": 12,
      "url": null
    }
  ],
  "index_version": "2026-11-06.1"
}
```

The user-facing message should not expose vector scores, internal prompts, local paths, or stack traces.

## 9. State model changes

Recommended answer-domain states:

- Shared: `LANG_SELECT`, profile states, complaint collection states, `SUMMARY`, and `CONFIRMED`.
- IVR: `IVR_MAIN_MENU`, `IVR_CATEGORY_MENU`, `IVR_QUESTION_LIST`, `IVR_ANSWER`.
- RAG: `RAG_AWAITING_QUESTION`, `RAG_PROCESSING`, `RAG_ANSWER`.

Add session metadata:

- `answer_mode` — snapshot of the deployment mode when the session begins.
- `last_question` — optional, with an appropriate retention limit.
- `rag_turns` — a small bounded list of user questions and source identifiers, not unrestricted prompts/documents.
- `last_answer_sources` — supports source display and diagnostics.

For production, replace the in-memory `_sessions` dictionary with a shared store such as Redis or a database with TTL and encryption. This is required for reliable multi-instance/serverless operation, independent of the RAG feature.

## 10. Failure and fallback behavior

| Condition | IVR behavior | RAG behavior |
|---|---|---|
| Invalid mode at startup | Fail startup | Fail startup |
| JSON missing/invalid | Fail readiness; do not show empty menus | Not applicable unless explicitly configured as fallback |
| Index missing/incompatible | Not applicable | Fail readiness and return temporary-unavailable message |
| LLM unavailable | IVR continues; translation may fall back according to policy | Do not fabricate; apologize and offer retry/contact/complaint |
| Retrieval has weak/no match | Not applicable | State that the approved sources do not contain enough information |
| PDF/website fetch fails during ingestion | Not applicable | Keep current active index; report failed source and do not promote a bad build |
| Unsupported user input | Resend current selectable options | Explain accepted text/question format or route recognized commands |

Do not silently fall back from RAG to a general-purpose LLM answer. An optional fallback from RAG to IVR must be explicitly configured and clearly presented to the user as browsing predefined FAQs, not as a RAG answer.

## 11. Security, privacy, and governance

- Consider PDF and website text untrusted. Prompt-injection text inside a source must never override application instructions.
- Use source allow-lists, checksums, review/approval status, and versioned promotion.
- Keep complaint attachments isolated from the shared knowledge corpus.
- Minimize logs containing phone numbers, questions, complaint details, retrieved chunks, and model prompts. Apply redaction, role-based access, retention, and deletion policies.
- Enforce maximum question size, rate limits per sender, model timeouts, retry limits, and request budgets.
- Use HTTPS and secret management for external APIs and vector-store credentials.
- Ensure content owners approve website/PDF use and that stale legal or policy material has review dates.
- For high-impact legal or consumer advice, show source/date information and a route to a qualified human; the bot should not claim professional representation.

## 12. Observability

Record structured, privacy-conscious metrics by mode:

- Request count, answer latency, error rate, and selected `ANSWER_MODE`.
- IVR category/question selection, invalid-input rate, and menu abandonment.
- RAG retrieval latency, generation latency, insufficient-evidence rate, source IDs used, index version, and escalation rate.
- Ingestion source count, pages/chunks indexed, extraction failures, duplicate content, and build/promotion status.

Use a correlation ID based on webhook/message processing, not a raw access token. Avoid storing full questions by default; use redacted samples only with an approved diagnostic policy.

## 13. Testing and acceptance criteria

### Configuration

- `ANSWER_MODE=IVR` initializes only the IVR answer service.
- `ANSWER_MODE=RAG` initializes only the RAG answer service and validates its index.
- Missing, blank, or unknown values fail startup in production.
- A session created under a previous mode is safely re-routed after deployment.

### IVR

- Every displayed category/question resolves to the correct JSON entry.
- Answers are obtained only through predefined selections.
- Typed free text cannot trigger generated answers or Groq category prediction.
- Pagination never exceeds WhatsApp list limits.
- Invalid and stale IDs do not crash or select unintended data.
- Complaint filing remains reachable from menus and answers.

### RAG

- A known question from each PDF returns a supported answer citing the correct document/page.
- A known website question cites the correct canonical page.
- An out-of-corpus question returns the insufficient-evidence response.
- Conflicting sources cause qualification or refusal according to policy, rather than an unsupported confident answer.
- Prompt-injection strings in a document or user question do not change system behavior.
- An unavailable model/index produces the designed fallback without losing the user session.
- Questions work in each supported language, with citations still pointing to the original source.
- Complaint filing, restart, and language commands bypass RAG correctly.

### Ingestion

- Duplicate sources are detected by canonical URL/checksum.
- Scanned PDFs are either OCR-processed or clearly reported as not indexed.
- Disallowed URLs and redirects are rejected.
- A failed build cannot replace the current active index.
- Removing a source and rebuilding removes it from retrieval results.

### Quality gate

Before production, create an approved evaluation set containing answerable, ambiguous, adversarial, multilingual, and unanswerable questions. Measure retrieval relevance, citation correctness, groundedness, refusal correctness, and response latency. `RAG_MIN_SCORE`, chunking, and `top_k` must be selected from these results rather than guessed.

## 14. Recommended delivery sequence

1. Add centralized configuration validation and the answer-service interface.
2. Move the existing strict predefined flow behind `IvrAnswerService`; remove free-text AI category prediction from strict IVR behavior.
3. Refactor `ingest.py` into manifest-driven remote-PDF ingestion with bounded temporary downloads, metadata, and versioned indexes.
4. Add the allow-listed website loader and ingestion security controls.
5. Implement retrieval and evidence gating independently of WhatsApp.
6. Add grounded generation, citations, and RAG conversation states.
7. Connect `RagAnswerService` to the existing webhook router.
8. Add shared persistent sessions, readiness checks, metrics, and production storage.
9. Run the evaluation suite and tune retrieval thresholds.
10. Deploy first in `IVR`, verify parity, then deploy a staging environment in `RAG` before production activation.

## 15. Decisions requiring confirmation before implementation

The design assumes the following; they should be confirmed before coding:

1. `ANSWER_MODE` is deployment-wide, not selected by each WhatsApp user.
2. Exactly one mode is active: `IVR` or `RAG`.
3. The welcome, language/profile collection, contact escalation, and complaint workflow remain available in both modes.
4. PDFs are not uploaded to or permanently stored by the application. Administrators provide stable HTTP(S) PDF URLs, which are fetched only by the controlled ingestion process.
5. PDF and website URLs are administrator-configured and ingested ahead of time; the bot does not browse or ingest arbitrary URLs during a conversation.
6. Strict IVR means no free-text category prediction and no model-generated answer.
7. RAG answers must be grounded in and cite configured sources; unsupported questions receive a transparent no-answer response.
8. Production deployment will use either a managed vector database or a build-time packaged, read-only index. The original PDF files remain on their existing remote hosts.
9. HTTPS PDF URLs are required for production. Any plain HTTP source requires an explicit security exception and accepts content-integrity risk.

