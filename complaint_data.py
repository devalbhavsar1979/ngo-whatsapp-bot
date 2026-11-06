"""
Complaint Data Store
Dynamic categories and FAQ questions loaded from JSON for the NGO WhatsApp Bot.
"""
import json
import os

# ── Dynamic Data Loading ───────────────────────────────────────────────
def load_qna_data():
    configured_path = os.getenv("QNA_JSON_PATH", "qna_data.json")
    json_path = configured_path if os.path.isabs(configured_path) else os.path.join(
        os.path.dirname(__file__), configured_path
    )
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Unable to load Q&A data from {json_path}: {e}") from e

RAW_QNA_DATA = load_qna_data()

# Build the CATEGORIES list dynamically
_categories_set = set()
for item in RAW_QNA_DATA:
    if "category" in item:
        _categories_set.add(item.get("category"))
CATEGORIES = sorted(list(_categories_set))

# Build CATEGORY_QUESTIONS dictionary
# Each key maps to a list of question strings
CATEGORY_QUESTIONS = {}
for item in RAW_QNA_DATA:
    cat = item.get("category")
    q = item.get("question")
    if cat and q:
        if cat not in CATEGORY_QUESTIONS:
            CATEGORY_QUESTIONS[cat] = []
        # Prevent duplicates if any
        if q not in CATEGORY_QUESTIONS[cat]:
            CATEGORY_QUESTIONS[cat].append(q)

def get_questions_for_category(category: str) -> list:
    """Get the list of FAQ questions for a given category."""
    return CATEGORY_QUESTIONS.get(category, [])

def get_dummy_answer(category: str, question: str) -> str:
    """Return the extracted answer for a given question from the JSON."""
    for item in RAW_QNA_DATA:
        if item.get("category") == category and item.get("question") == question:
            advice = item.get("answer")
            return (
                f"📋 *Regarding your query:*\n"
                f"_{question}_\n\n"
                f"💡 *Guidance:*\n"
                f"{advice}\n\n"
                f"📞 *Helpline:* 18002330332\n"
                f"📧 *Email:* complaints@cercindia.org\n\n"
                f"If this does not resolve your issue, you can file a formal complaint through this bot."
            )
            
    # Fallback if somehow not found
    return (
        f"📋 *Regarding your query:*\n"
        f"_{question}_\n\n"
        f"💡 *Guidance:*\n"
        f"You can file a complaint at the nearest Consumer Forum, call Helpline 18002330332 or email complaints@cercindia.org.\n\n"
        f"📞 *Helpline:* 18002330332\n"
        f"📧 *Email:* complaints@cercindia.org\n\n"
        f"If this does not resolve your issue, you can file a formal complaint through this bot."
    )
