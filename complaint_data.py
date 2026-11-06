"""Compatibility helpers backed by the configurable IVR JSON store."""

from ivr_config import IVR_CONFIG

CATEGORIES = [
    IVR_CONFIG.text(category["label"])
    for group in IVR_CONFIG.groups()
    for category in IVR_CONFIG.categories(group["id"])
]

CATEGORY_QUESTIONS = {
    IVR_CONFIG.text(category["label"]): [
        IVR_CONFIG.text(faq["question"]) for faq in IVR_CONFIG.faqs(category["id"])
    ]
    for category in IVR_CONFIG.categories_by_id.values()
}


def get_questions_for_category(category_id):
    return [IVR_CONFIG.text(faq["question"]) for faq in IVR_CONFIG.faqs(category_id)]


def get_dummy_answer(category_id, question):
    for faq in IVR_CONFIG.faqs(category_id):
        if IVR_CONFIG.text(faq["question"]) == question:
            return IVR_CONFIG.text(faq["answer"])
    return "The selected guidance could not be found. Please return to the menu."
