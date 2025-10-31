"""Orchestration 엔트리포인트."""

from __future__ import annotations

import logging
from typing import Any

from src.orchestration.composer import render_answer
from src.orchestration.ports import Compute, Retriever
from src.orchestration.router import route
from src.orchestration.state import OrchestrationState

logger = logging.getLogger(__name__)


def run(
    query: str,
    *,
    retriever: Retriever,
    compute: Compute,
    inputs: dict[str, Any] | None = None,
) -> str:
    """CRAG 파이프라인을 실행하여 최종 응답 문자열을 생성한다."""

    state = OrchestrationState(user_query=query, inputs=inputs or {})

    state = route(state, retriever=retriever)

    if state.mode == "calc":
        state = _run_compute(state, compute=compute)

    return render_answer(state)


def _run_compute(state: OrchestrationState, *, compute: Compute) -> OrchestrationState:
    """계산형 파이프라인을 실행한다."""

    try:
        result = compute.run(state.inputs)
    except Exception as exc:  # pragma: no cover - 상위에서 예외 처리
        logger.exception("Compute 모듈 실행 실패: inputs=%s", state.inputs)
        raise RuntimeError("계산 엔진 실행 중 오류가 발생했습니다.") from exc

    if not isinstance(result, dict):
        logger.error("Compute 결과가 dict가 아님: %r", result)
        raise TypeError("Compute 모듈은 dict 결과를 반환해야 합니다.")

    state.calc = result

    sources = result.get("sources")
    if isinstance(sources, list):
        extracted = []
        for item in sources:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "계산 엔진")
            date = str(item.get("date") or "-")
            entry = {"name": name, "date": date}
            if entry not in extracted:
                extracted.append(entry)
        state.sources = extracted

    if not state.sources:
        state.sources = [{"name": "계산 엔진", "date": "-"}]

    logger.debug("Compute 파이프라인 완료. keys=%s", sorted(state.calc.keys()))
    return state
