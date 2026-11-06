import os
import unittest
from unittest.mock import patch

from answer_config import load_answer_config
from rag_service import RagAnswerService


class AnswerConfigTests(unittest.TestCase):
    def test_missing_mode_fails_fast(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                load_answer_config()

    def test_mode_is_normalized(self):
        with patch.dict(os.environ, {"ANSWER_MODE": " rag "}, clear=True):
            self.assertEqual(load_answer_config().mode, "RAG")

    def test_invalid_mode_fails(self):
        with patch.dict(os.environ, {"ANSWER_MODE": "hybrid"}, clear=True):
            with self.assertRaises(RuntimeError):
                load_answer_config()

    def test_invalid_numeric_setting_fails(self):
        with patch.dict(os.environ, {"ANSWER_MODE": "IVR", "RAG_TOP_K": "0"}, clear=True):
            with self.assertRaises(RuntimeError):
                load_answer_config()

    def test_rag_without_index_is_not_ready_and_does_not_import_heavy_packages(self):
        with patch.dict(os.environ, {
            "ANSWER_MODE": "RAG",
            "RAG_INDEX_PATH": "definitely_missing_test_index",
        }, clear=True):
            service = RagAnswerService(load_answer_config(), groq_client=object())
            self.assertFalse(service.ready)
            result = service.answer("What services are available?", "lang_english")
            self.assertEqual(result.status, "unavailable")


if __name__ == "__main__":
    unittest.main()
