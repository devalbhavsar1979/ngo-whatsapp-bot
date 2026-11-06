# Configurable IVR Design

## 1. Objective

Move all IVR knowledge and navigation configuration out of Python source code and into one administrator-maintained JSON file.

The JSON configuration should control:

- Product and Service menu entries.
- Menu ordering and enabled/disabled status.
- Categories and their stable identifiers.
- Category display names.
- Predefined FAQ questions and answers.
- FAQ ordering and enabled/disabled status.
- Mapping between menu entries and FAQ categories.
- Optional multilingual labels and content.

This document is a design only. It does not change the current application.

## 2. Current arrangement

The current IVR information is divided between multiple files:

- `app.py`
  - `PRODUCT_CATEGORIES`
  - `SERVICE_CATEGORIES`
  - `DISPLAY_TO_DATA_CATEGORY`
  - Product, Service, category, and FAQ navigation behavior
- `qna_data.json`
  - FAQ category names
  - Questions
  - Answers
- `complaint_data.py`
  - Loads `qna_data.json`
  - Builds categories and question lists
  - Looks up selected answers

This creates several maintenance risks:

- A category may be added to JSON but omitted from the Product/Service menu.
- A display-to-data mapping may be missing or misspelled.
- Renaming a category can break FAQ lookup.
- Ordering is partly controlled by Python and partly by JSON.
- A non-developer cannot safely maintain the complete IVR structure in one place.

## 3. Proposed configuration

Introduce one file:

```text
ivr_config.json
```

Configure its location through:

```dotenv
IVR_CONFIG_PATH=ivr_config.json
```

`IVR_CONFIG_PATH` is used only when:

```dotenv
ANSWER_MODE=IVR
```

The recommended configuration structure is hierarchical:

```text
IVR configuration
├── configuration metadata
├── language settings
├── main menu settings
├── Product group
│   └── categories
│       └── predefined FAQs
└── Service group
    └── categories
        └── predefined FAQs
```

Keeping FAQs inside their category eliminates the separate display-to-data mapping currently required by `app.py`.

## 4. Proposed JSON schema

Example `ivr_config.json`:

```json
{
  "schema_version": "1.0",
  "config_version": "2026-11-06.1",
  "default_language": "en",
  "supported_languages": ["en", "hi", "gu", "mr"],
  "main_menu": {
    "prompt": {
      "en": "Select a category type:"
    },
    "groups": [
      {
        "id": "products",
        "label": {
          "en": "Products"
        },
        "icon": "📦",
        "order": 10,
        "enabled": true,
        "categories": [
          {
            "id": "vehicle",
            "label": {
              "en": "Automobile"
            },
            "faq_heading": {
              "en": "Vehicle FAQs"
            },
            "order": 10,
            "enabled": true,
            "faqs": [
              {
                "id": "vehicle_higher_service_charge",
                "question": {
                  "en": "The service centre charged more than the estimate. What should I do?"
                },
                "answer": {
                  "en": "Ask for a detailed bill with an item-wise breakup. Check whether you approved additional repairs. If no consent was given, complain to the service centre or manufacturer and consider approaching the appropriate Consumer Commission."
                },
                "order": 10,
                "enabled": true
              }
            ]
          },
          {
            "id": "solar_panel",
            "label": {
              "en": "Solar Panel"
            },
            "order": 20,
            "enabled": true,
            "faqs": []
          }
        ]
      },
      {
        "id": "services",
        "label": {
          "en": "Services"
        },
        "icon": "🛠️",
        "order": 20,
        "enabled": true,
        "categories": [
          {
            "id": "banking_services",
            "label": {
              "en": "Banking"
            },
            "order": 10,
            "enabled": true,
            "faqs": [
              {
                "id": "banking_unauthorized_transaction",
                "question": {
                  "en": "What should I do about an unauthorized bank transaction?"
                },
                "answer": {
                  "en": "Notify the bank immediately, block the affected payment method, preserve transaction records, and submit a written complaint."
                },
                "order": 10,
                "enabled": true
              }
            ]
          }
        ]
      }
    ]
  },
  "actions": {
    "file_complaint": {
      "enabled": true,
      "label": {
        "en": "File Complaint"
      }
    },
    "change_language": {
      "enabled": true,
      "label": {
        "en": "Change Language"
      }
    },
    "contact_support": {
      "enabled": true,
      "label": {
        "en": "Contact Support"
      }
    }
  },
  "support": {
    "phone": "18002330332",
    "email": "complaints@cercindia.org",
    "hours": {
      "en": "Monday-Friday, 10:30 AM-5:30 PM"
    }
  }
}
```

## 5. Configuration fields

### Root fields

| Field | Required | Description |
|---|---:|---|
| `schema_version` | Yes | Defines the JSON structure understood by the application. |
| `config_version` | Yes | Administrator-controlled content version used in logs and diagnostics. |
| `default_language` | Yes | Language used when a translation is absent. |
| `supported_languages` | Yes | Languages offered by the IVR. |
| `main_menu` | Yes | Main IVR prompt and menu groups. |
| `actions` | Yes | Shared IVR actions such as filing a complaint. |
| `support` | Yes | Configurable contact information shown in answers or escalation messages. |

### Group fields

Groups replace the hard-coded `PRODUCT_CATEGORIES` and `SERVICE_CATEGORIES` lists.

| Field | Required | Description |
|---|---:|---|
| `id` | Yes | Stable machine identifier such as `products` or `services`. |
| `label` | Yes | User-facing multilingual label. |
| `icon` | No | Optional display icon. |
| `order` | Yes | Numeric display order. |
| `enabled` | Yes | Allows a group to be hidden without deleting it. |
| `categories` | Yes | Categories belonging to the group. |

The initial version can retain exactly two group IDs, `products` and `services`. The structure also permits additional groups later without changing the FAQ format.

### Category fields

| Field | Required | Description |
|---|---:|---|
| `id` | Yes | Stable unique identifier used in callbacks and session data. |
| `label` | Yes | User-facing multilingual category name. |
| `faq_heading` | No | Optional heading for the FAQ list. |
| `order` | Yes | Category order inside its group. |
| `enabled` | Yes | Whether the category is visible. |
| `faqs` | Yes | Predefined FAQs for the category. |

Stable IDs remove the need for `DISPLAY_TO_DATA_CATEGORY`. For example, `vehicle` remains unchanged even if its English label changes from `Automobile` to `Vehicles`.

### FAQ fields

| Field | Required | Description |
|---|---:|---|
| `id` | Yes | Stable unique FAQ identifier. |
| `question` | Yes | Multilingual predefined question. |
| `answer` | Yes | Multilingual predefined answer. |
| `order` | Yes | Display order inside the category. |
| `enabled` | Yes | Allows temporary removal without deleting content. |

FAQ callback IDs must use the stable FAQ ID rather than the question's array index. Array-index IDs such as `faq_3` can select the wrong FAQ after administrators reorder the file.

## 6. Multilingual strategy

Two approaches are possible.

### Recommended: translations in JSON

```json
"label": {
  "en": "Automobile",
  "hi": "ऑटोमोबाइल",
  "gu": "ઓટોમોબાઇલ",
  "mr": "ऑटोमोबाईल"
}
```

Advantages:

- Deterministic IVR content.
- No LLM call is required for menu or FAQ translation.
- Administrators can review and approve legal/consumer wording.
- IVR continues working if Groq is unavailable.

Fallback order:

1. User-selected language.
2. `default_language`.
3. Configuration validation failure when neither is present.

### Transitional option: English-only JSON

The first migration may contain only `en` values and continue using the existing translation service for missing languages. This is easier initially but makes IVR output dependent on an LLM and is less deterministic. Approved translations should eventually be stored in JSON.

## 7. Loading and runtime behavior

At startup in IVR mode, the application should:

1. Read `IVR_CONFIG_PATH`.
2. Parse the JSON exactly once.
3. Validate the complete configuration.
4. Build immutable in-memory lookup tables by ID.
5. Log `schema_version` and `config_version`.
6. Mark `/health` not ready if configuration is invalid.

Suggested in-memory indexes:

```text
group_by_id
category_by_id
faq_by_id
categories_by_group_id
faqs_by_category_id
```

The application should not repeatedly scan or reload the file for each WhatsApp message. Configuration changes become active after redeployment or process restart.

## 8. WhatsApp identifier design

Interactive callback identifiers should contain stable IDs:

```text
group:products
category:vehicle
faq:vehicle_higher_service_charge
category-page:products:2
faq-page:vehicle:2
action:file_complaint
action:back
```

The exact separator is an implementation decision. Validation must ensure the resulting callback IDs remain within Meta's identifier limits.

Do not derive callback IDs from translated labels. Labels can change, contain Unicode, or be duplicated; stable IDs cannot.

## 9. WhatsApp presentation constraints

Configuration validation and menu rendering must account for WhatsApp limits already handled by the current application:

- Interactive lists allow at most 10 rows across all sections.
- Reply-button messages allow at most 3 buttons.
- Button titles and list titles have strict length limits.
- FAQ question descriptions and message bodies also have length limits.

The application should continue paginating categories and FAQs automatically. Administrators should not manually create pagination entries in JSON.

Long labels should produce a validation warning or error rather than being silently truncated into ambiguous duplicates. Long FAQ answers may be split into multiple plain-text messages if required.

## 10. Validation requirements

Startup validation should reject:

- Invalid JSON.
- Unsupported `schema_version`.
- Missing required root fields.
- Duplicate group, category, or FAQ IDs.
- IDs containing unsupported characters.
- A category appearing in more than one group unless explicitly supported later.
- An FAQ assigned to an unknown category.
- Enabled categories with no enabled FAQs, unless empty categories are explicitly allowed.
- Missing default-language labels, questions, or answers.
- Duplicate order numbers where deterministic order is required.
- Labels that cannot fit WhatsApp controls.
- Invalid support email or phone formats.
- More top-level reply buttons than WhatsApp permits.

Recommended ID format:

```text
^[a-z][a-z0-9_]{1,63}$
```

Validation errors should identify the JSON location, for example:

```text
main_menu.groups[1].categories[3].faqs[2].answer.en is required
```

The application must fail readiness rather than start with partially loaded menus.

## 11. Administrative workflow

Recommended update process:

1. Edit `ivr_config.json` on a separate branch.
2. Run a configuration validation command locally or in CI.
3. Review the generated menu/FAQ summary.
4. Obtain content approval where answers contain legal or consumer guidance.
5. Merge and deploy.
6. Confirm `/health` reports the expected `config_version`.
7. Test Product, Service, pagination, FAQ answers, Back, and File Complaint paths.

Configuration should remain in source control so changes have history, review, and rollback support.

## 12. Migration from the current files

Migration should be performed in controlled stages:

1. Extract `PRODUCT_CATEGORIES` and `SERVICE_CATEGORIES` from `app.py` into groups and category entries.
2. Use `DISPLAY_TO_DATA_CATEGORY` to connect each existing menu label with its current `qna_data.json` category.
3. Assign a stable `id` to every group, category, and FAQ.
4. Move each `qna_data.json` question and answer into its category's `faqs` array.
5. Preserve existing menu and FAQ order explicitly through `order` values.
6. Compare counts between old and new data:
   - Groups
   - Categories
   - Questions
   - Answers
7. Run parity tests proving every current selection returns the same answer.
8. Switch IVR loading to `ivr_config.json` only after parity validation.
9. Retain the old JSON for one release as a rollback artifact, then remove it when no longer referenced.

The migration tool, if created later, should report unmapped menu categories instead of guessing their destination.

## 13. Compatibility and session handling

Existing sessions may contain array-index callback IDs or category display names. After the configurable IVR is deployed:

- New outgoing messages must use stable configuration IDs.
- Old callbacks should be treated as stale and return the user to the appropriate menu.
- The bot must not interpret an old array index against newly reordered data.
- Session records should store `config_version` and stable category/FAQ IDs.
- If a session's configuration version differs from the active version, reset its IVR navigation state while retaining profile data when appropriate.

## 14. Health and diagnostics

For IVR mode, `/health` should report:

```json
{
  "status": "healthy",
  "answer_mode": "IVR",
  "ivr_ready": true,
  "ivr_schema_version": "1.0",
  "ivr_config_version": "2026-11-06.1"
}
```

Do not expose the full configuration or FAQ answers through the health endpoint.

Startup logs may safely include:

- Configuration version.
- Number of enabled groups.
- Number of enabled categories.
- Number of enabled FAQs.
- Validation failures without secrets or personal data.

## 15. Testing requirements

### Configuration tests

- Valid configuration loads successfully.
- Invalid JSON fails readiness.
- Duplicate IDs are rejected.
- Missing default-language content is rejected.
- Disabled groups, categories, and FAQs are excluded.
- Ordering is deterministic.

### Navigation tests

- Product and Service groups show the configured categories.
- Every category opens its own configured FAQ list.
- Every FAQ ID resolves to the correct configured answer.
- Pagination never exceeds WhatsApp limits.
- Back navigation returns to the correct configured parent.
- File Complaint remains available where configured.
- Stale or forged IDs cannot select unrelated content.

### Migration parity tests

- The new category count matches the intended current category count.
- Every existing `qna_data.json` record is migrated or explicitly excluded.
- Existing displayed Product/Service entries resolve to equivalent categories.
- Existing FAQ selections produce equivalent answers.

## 16. Recommended decisions

1. Use one hierarchical `ivr_config.json` file initially.
2. Use stable IDs everywhere; never use array indexes or labels as identity.
3. Store Product/Service grouping directly on the category hierarchy, eliminating `DISPLAY_TO_DATA_CATEGORY`.
4. Store ordering and enabled flags explicitly.
5. Store approved translations in JSON over time, with English as the initial required language.
6. Validate the complete configuration during startup and CI.
7. Activate configuration changes only through reviewed deployments, not live unauthenticated edits.
8. Keep complaint workflow implementation in code; configure only its menu label, visibility, and support contact details in this IVR file.

## 17. Scope boundary

The proposed JSON controls IVR content and navigation data. It should not contain:

- WhatsApp access tokens.
- Groq or other API keys.
- Email service credentials.
- Google service-account credentials.
- Executable Python expressions.
- Arbitrary webhook URLs.
- Complaint records or user personal data.

Secrets remain environment variables. Conversation processing, validation, pagination, security, complaint submission, email delivery, and persistence remain application code.
