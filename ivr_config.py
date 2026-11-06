"""Validated, immutable IVR configuration loaded from JSON at startup."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
SUPPORTED_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class IvrConfigStore:
    raw: dict
    groups_by_id: dict
    categories_by_id: dict
    faqs_by_id: dict
    category_group: dict

    @property
    def schema_version(self): return self.raw["schema_version"]

    @property
    def config_version(self): return self.raw["config_version"]

    @property
    def default_language(self): return self.raw["default_language"]

    def text(self, values, language="en"):
        if not isinstance(values, dict): return str(values or "")
        return values.get(language) or values.get(self.default_language) or ""

    def groups(self):
        return sorted((item for item in self.groups_by_id.values() if item["enabled"]),
                      key=lambda item: (item["order"], item["id"]))

    def categories(self, group_id):
        group = self.groups_by_id.get(group_id)
        if not group or not group["enabled"]: return []
        return sorted((item for item in group["categories"] if item["enabled"]),
                      key=lambda item: (item["order"], item["id"]))

    def faqs(self, category_id):
        category = self.categories_by_id.get(category_id)
        if not category or not category["enabled"]: return []
        return sorted((item for item in category["faqs"] if item["enabled"]),
                      key=lambda item: (item["order"], item["id"]))


def _require(condition, message):
    if not condition: raise RuntimeError(f"Invalid IVR configuration: {message}")


def _localized(value, path, language):
    _require(isinstance(value, dict), f"{path} must be an object")
    _require(value.get(language), f"{path}.{language} is required")


def load_ivr_config(path=None):
    configured = path or os.getenv("IVR_CONFIG_PATH", "ivr_config.json")
    config_path = Path(configured)
    if not config_path.is_absolute(): config_path = Path(__file__).resolve().parent / config_path
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Unable to load IVR configuration from {config_path}: {exc}") from exc
    _require(raw.get("schema_version") == SUPPORTED_SCHEMA_VERSION,
             f"unsupported schema_version {raw.get('schema_version')!r}")
    _require(isinstance(raw.get("config_version"), str) and raw["config_version"],
             "config_version is required")
    language = raw.get("default_language")
    _require(language in raw.get("supported_languages", []), "default_language must be supported")
    menu = raw.get("main_menu")
    _require(isinstance(menu, dict), "main_menu is required")
    _localized(menu.get("prompt"), "main_menu.prompt", language)
    groups = menu.get("groups")
    _require(isinstance(groups, list) and groups, "main_menu.groups must not be empty")
    groups_by_id, categories_by_id, faqs_by_id, category_group = {}, {}, {}, {}
    for gi, group in enumerate(groups):
        path_g, group_id = f"main_menu.groups[{gi}]", group.get("id")
        _require(isinstance(group_id, str) and ID_PATTERN.fullmatch(group_id), f"{path_g}.id is invalid")
        _require(group_id not in groups_by_id, f"duplicate group id {group_id}")
        _localized(group.get("label"), f"{path_g}.label", language)
        _require(isinstance(group.get("order"), int), f"{path_g}.order must be an integer")
        _require(isinstance(group.get("enabled"), bool), f"{path_g}.enabled must be boolean")
        categories = group.get("categories")
        _require(isinstance(categories, list), f"{path_g}.categories must be a list")
        groups_by_id[group_id] = group
        for ci, category in enumerate(categories):
            path_c, category_id = f"{path_g}.categories[{ci}]", category.get("id")
            _require(isinstance(category_id, str) and ID_PATTERN.fullmatch(category_id), f"{path_c}.id is invalid")
            _require(category_id not in categories_by_id, f"duplicate category id {category_id}")
            _localized(category.get("label"), f"{path_c}.label", language)
            _require(isinstance(category.get("order"), int), f"{path_c}.order must be an integer")
            _require(isinstance(category.get("enabled"), bool), f"{path_c}.enabled must be boolean")
            faqs = category.get("faqs")
            _require(isinstance(faqs, list), f"{path_c}.faqs must be a list")
            categories_by_id[category_id], category_group[category_id] = category, group_id
            for fi, faq in enumerate(faqs):
                path_f, faq_id = f"{path_c}.faqs[{fi}]", faq.get("id")
                _require(isinstance(faq_id, str) and ID_PATTERN.fullmatch(faq_id), f"{path_f}.id is invalid")
                _require(faq_id not in faqs_by_id, f"duplicate FAQ id {faq_id}")
                _localized(faq.get("question"), f"{path_f}.question", language)
                _localized(faq.get("answer"), f"{path_f}.answer", language)
                _require(isinstance(faq.get("order"), int), f"{path_f}.order must be an integer")
                _require(isinstance(faq.get("enabled"), bool), f"{path_f}.enabled must be boolean")
                faqs_by_id[faq_id] = faq
    return IvrConfigStore(raw, groups_by_id, categories_by_id, faqs_by_id, category_group)


IVR_CONFIG = load_ivr_config()
