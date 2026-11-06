"""One-time, deterministic migration from legacy IVR data to ivr_config.json."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PRODUCTS = [
    ("Automobile", "Vehicle"),
    ("Electrical Home Appliances", "Electrical & Electronic App."),
    ("Solar Panel", "Solar Panel"),
    ("Mobile Handset & Electronics", "Mobile Handset"),
    ("E- Commerce", "E commerce"),
    ("Weight, Size & Description", "Weights & Measures"),
]

SERVICES = [
    ("Airline", "Airlines"),
    ("Banking (Credit Card, Investments, and loans)", "Banking Services"),
    ("Insurances (Life, Health, Travel, Motor, etc.)", "Insurances (Life, Health, Travel, Motor, etc.)"),
    ("Internet, Mobile & telecom services", "Internet Services"),
    ("Education", "Educational Institute"),
    ("Taxi, Bus, Railway", "Railway"),
    ("Tour Packages (Tour, Vacation Club, and Hotel)", "Transport Tours & Travels"),
    ("Real Estate", "Housing/ Builder"),
    ("Post & courier", "Postal Services"),
    ("LPG & Gas", "LPG, PNG & Petrol"),
    ("Electricity Company", "Electricity Boards"),
    ("Advocate & Court Procedure", "Advocate"),
]


def slug(value):
    result = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return result[:55] or "item"


def build_category(label, data_name, records, order):
    category_id = slug(data_name)
    faqs = []
    for number, item in enumerate(records[data_name], start=1):
        faqs.append({
            "id": f"{category_id}_faq_{number:03d}",
            "question": {"en": item["question"]},
            "answer": {"en": item["answer"]},
            "order": number * 10,
            "enabled": True,
        })
    return {
        "id": category_id,
        "label": {"en": label},
        "data_name": data_name,
        "order": order * 10,
        "enabled": True,
        "faqs": faqs,
    }


def main():
    legacy = json.loads((ROOT / "qna_data.json").read_text(encoding="utf-8"))
    records = {}
    for item in legacy:
        records.setdefault(item["category"], []).append(item)

    assigned = {data_name for _, data_name in PRODUCTS + SERVICES}
    other_names = sorted(set(records) - assigned)
    groups = []
    for group_id, label, icon, definitions, group_order in (
        ("products", "Products", "📦", PRODUCTS, 10),
        ("services", "Services", "🛠️", SERVICES, 20),
        ("other", "Other Categories", "📚", [(name, name) for name in other_names], 30),
    ):
        categories = [
            build_category(display, data_name, records, number)
            for number, (display, data_name) in enumerate(definitions, start=1)
        ]
        groups.append({
            "id": group_id,
            "label": {"en": label},
            "icon": icon,
            "order": group_order,
            "enabled": True,
            "categories": categories,
        })

    config = {
        "schema_version": "1.0",
        "config_version": "2026-11-06.1",
        "default_language": "en",
        "supported_languages": ["en", "hi", "gu", "mr"],
        "main_menu": {
            "prompt": {"en": "Select a category type:"},
            "groups": groups,
        },
        "actions": {
            "file_complaint": {"enabled": True, "label": {"en": "File Complaint"}},
            "change_language": {"enabled": True, "label": {"en": "Change Language"}},
            "contact_support": {"enabled": True, "label": {"en": "Contact Support"}},
        },
        "support": {
            "phone": "18002330332",
            "email": "complaints@cercindia.org",
            "hours": {"en": "Monday-Friday, 10:30 AM-5:30 PM"},
        },
    }
    output = ROOT / "ivr_config.json"
    output.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created {output.name}: {len(groups)} groups, {len(records)} categories, {len(legacy)} FAQs")


if __name__ == "__main__":
    main()
