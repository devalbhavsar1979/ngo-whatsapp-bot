"""Validated configuration for IVR/RAG answer behaviour."""

import os
from dataclasses import dataclass


VALID_ANSWER_MODES = {"IVR", "RAG"}


@dataclass(frozen=True)
class AnswerConfig:
    mode: str
    qna_json_path: str
    rag_index_path: str
    rag_embedding_model: str
    rag_llm_model: str
    rag_top_k: int
    rag_min_score: float
    rag_max_context_chars: int


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


def _number(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


def load_answer_config() -> AnswerConfig:
    raw_mode = os.getenv("ANSWER_MODE")
    if raw_mode is None or not raw_mode.strip():
        raise RuntimeError("ANSWER_MODE is required; set it to IVR or RAG")
    mode = raw_mode.strip().upper()
    if mode not in VALID_ANSWER_MODES:
        raise RuntimeError(
            f"Invalid ANSWER_MODE={mode!r}; expected one of {sorted(VALID_ANSWER_MODES)}"
        )

    return AnswerConfig(
        mode=mode,
        qna_json_path=os.getenv("QNA_JSON_PATH", "qna_data.json").strip(),
        rag_index_path=os.getenv("RAG_INDEX_PATH", "ngo_index").strip(),
        rag_embedding_model=os.getenv(
            "RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
        ).strip(),
        rag_llm_model=os.getenv(
            "RAG_LLM_MODEL", "llama-3.3-70b-versatile"
        ).strip(),
        rag_top_k=_integer("RAG_TOP_K", 5, 1, 20),
        rag_min_score=_number("RAG_MIN_SCORE", 0.35, 0.0, 1.0),
        rag_max_context_chars=_integer(
            "RAG_MAX_CONTEXT_CHARS", 12000, 1000, 50000
        ),
    )
