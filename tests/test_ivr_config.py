import json
import unittest
from pathlib import Path

from ivr_config import IVR_CONFIG, load_ivr_config

ROOT = Path(__file__).resolve().parents[1]


class IvrConfigTests(unittest.TestCase):
    def test_configuration_counts(self):
        self.assertEqual(len(IVR_CONFIG.groups_by_id), 3)
        self.assertEqual(len(IVR_CONFIG.categories_by_id), 36)
        self.assertEqual(len(IVR_CONFIG.faqs_by_id), 192)

    def test_all_ids_are_unique(self):
        all_ids = (list(IVR_CONFIG.groups_by_id) +
                   list(IVR_CONFIG.categories_by_id) +
                   list(IVR_CONFIG.faqs_by_id))
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_every_legacy_record_was_migrated_exactly(self):
        legacy = json.loads((ROOT / "qna_data.json").read_text(encoding="utf-8"))
        migrated = []
        for category in IVR_CONFIG.categories_by_id.values():
            for faq in category["faqs"]:
                migrated.append((
                    category["data_name"],
                    IVR_CONFIG.text(faq["question"]),
                    IVR_CONFIG.text(faq["answer"]),
                ))
        original = [(item["category"], item["question"], item["answer"]) for item in legacy]
        self.assertCountEqual(migrated, original)

    def test_product_service_and_other_groups_are_available(self):
        self.assertEqual(
            [group["id"] for group in IVR_CONFIG.groups()],
            ["products", "services", "other"],
        )
        self.assertEqual(len(IVR_CONFIG.categories("products")), 6)
        self.assertEqual(len(IVR_CONFIG.categories("services")), 12)
        self.assertEqual(len(IVR_CONFIG.categories("other")), 18)

    def test_file_can_be_reloaded_and_validated(self):
        reloaded = load_ivr_config(ROOT / "ivr_config.json")
        self.assertEqual(reloaded.config_version, IVR_CONFIG.config_version)

    def test_pagination_never_exceeds_whatsapp_row_limit(self):
        page_size = 6
        for group in IVR_CONFIG.groups():
            categories = IVR_CONFIG.categories(group["id"])
            for start in range(0, len(categories), page_size):
                category_rows = len(categories[start:start + page_size])
                page = start // page_size
                navigation_rows = 2  # File Complaint and Back
                if page > 0:
                    navigation_rows += 1
                if start + page_size < len(categories):
                    navigation_rows += 1
                self.assertLessEqual(category_rows + navigation_rows, 10)


if __name__ == "__main__":
    unittest.main()
