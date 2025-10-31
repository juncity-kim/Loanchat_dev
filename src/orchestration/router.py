"""간단한 intent 라우터.

질문을 계산형/정보형으로 분기하고, 정보형일 경우 Retriever 검색 결과를
OrchestrationState에 반영한다.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from src.orchestration.ports import Retriever
from src.orchestration.state import OrchestrationState

logger = logging.getLogger(__name__)

_CALC_KEYS = ("얼마", "한도", "가능", "LTV", "DTI", "DSR", "상환", "금리", "만기")
_HIGH_CONFIDENCE = 0.75
_LOW_CONFIDENCE = 0.40


def route(state: OrchestrationState, *, retriever: Retriever) -> OrchestrationState:
    """질문 유형에 따라 계산 혹은 검색 파이프라인으로 라우팅한다."""

    query = state.user_query.strip()
    state.mode = "calc" if any(key in query for key in _CALC_KEYS) else "info"

    if state.mode == "info":
        logger.debug("정보형 질의로 분류되어 Retriever 호출: query=%s", query)
        try:
            raw_docs = retriever.search(query)
        except Exception:  # pragma: no cover - 구체 원인은 로그로 확인
            logger.exception("Retriever 검색 실패 - query=%s", query)
            state.docs = []
            state.sources = []
            return state

        normalized_docs = [_normalize_doc(doc) for doc in raw_docs if isinstance(doc, dict)]
        normalized_docs = [doc for doc in normalized_docs if doc is not None]

        eligible_docs = [doc for doc in normalized_docs if doc["score"] >= _LOW_CONFIDENCE]
        if not eligible_docs:
            logger.info("임계치 미만 검색 결과 - query=%s", query)
            state.docs = []
            state.sources = []
            return state

        eligible_docs.sort(key=lambda doc: doc["score"], reverse=True)
        state.docs = eligible_docs
        state.sources = _build_sources(eligible_docs)

        confidence = eligible_docs[0]["score"]
        logger.debug(
            "Retriever 결과 %d건, 최고 신뢰도 %.2f (query=%s)",
            len(eligible_docs),
            confidence,
            query,
        )

        if confidence < _HIGH_CONFIDENCE:
            logger.info(
                "최고 신뢰도 %.2f가 임계치 %.2f 미만 - 추가 확인 필요 (query=%s)",
                confidence,
                _HIGH_CONFIDENCE,
                query,
            )

    return state


def _normalize_doc(doc: dict[str, Any]) -> dict[str, Any] | None:
    """Retriever 결과를 공통 포맷(dict)으로 정규화한다."""

    if not doc:
        return None

    normalized = deepcopy(doc)

    score = _extract_score(normalized)
    text = _extract_text(normalized)
    source = _extract_source(normalized)
    date = _extract_date(normalized)

    normalized["score"] = score
    normalized.setdefault("text", text)
    normalized.setdefault("source", source)
    normalized.setdefault("date", date)

    return normalized


def _extract_score(doc: dict[str, Any]) -> float:
    raw_score = (
        doc.get("score")
        or doc.get("confidence")
        or doc.get("relevance")
        or doc.get("metadata", {}).get("score")
    )
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = 0.0
    return max(0.0, min(score, 1.0))


def _extract_text(doc: dict[str, Any]) -> str:
    text = doc.get("text") or doc.get("content") or doc.get("chunk") or ""
    return str(text).strip()


def _extract_source(doc: dict[str, Any]) -> str:
    metadata = doc.get("metadata") or {}
    return str(
        metadata.get("source")
        or metadata.get("origin")
        or metadata.get("publisher")
        or doc.get("source")
        or doc.get("title")
        or "자료 미상"
    )


def _extract_date(doc: dict[str, Any]) -> str:
    metadata = doc.get("metadata") or {}
    return str(metadata.get("date") or metadata.get("published_at") or doc.get("date") or "-")


def _build_sources(docs: list[dict[str, Any]]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for doc in docs[:5]:
        name = str(doc.get("source") or "자료 미상")
        date = str(doc.get("date") or "-")
        entry = {"name": name, "date": date}
        if entry not in sources:
            sources.append(entry)
    return sources
