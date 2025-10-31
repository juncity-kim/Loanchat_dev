"""응답 조립(composer)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

from jinja2 import Template

from src.orchestration.state import OrchestrationState

logger = logging.getLogger(__name__)

# prompts 디렉터리: 프로젝트 루트/config/prompts 기준 (배포 안정)
PROMPTS = Path(__file__).resolve().parents[2] / "config" / "prompts"

_FALLBACK = """\
{% if mode == "calc" -%}
계산 결과
- 예상 한도: {{ limit_kr }}
- 금리: {{ rate }}%
- 기간: {{ term_years }}년
- 방식: {{ repay_type }}
{%- else -%}
요약
{{ summary }}

내용
{{ details }}
{%- endif -%}
"""

_INFO_HIGH_CONFIDENCE = 0.75


def render_answer(state: OrchestrationState) -> str:
    """상태를 기반으로 최종 응답 문자열을 생성한다."""

    template = _load_template()

    if state.mode == "calc":
        payload = _build_calc_payload(state)
    else:
        payload = _build_info_payload(state)

    logger.debug("Composer 렌더링 - mode=%s keys=%s", payload["mode"], sorted(payload.keys()))
    return template.render(**payload)


def _load_template() -> Template:
    path = PROMPTS / "composer_answer.txt"
    if path.exists():
        return Template(path.read_text(encoding="utf-8"))
    logger.warning("composer_answer.txt을 찾지 못해 기본 템플릿 사용")
    return Template(_FALLBACK)


def _build_calc_payload(state: OrchestrationState) -> dict[str, Any]:
    calc = state.calc or {}

    limit = _format_currency(
        calc.get("limit_kr")
        or calc.get("limit")
        or calc.get("max_amount")
        or calc.get("expected_limit")
    )
    monthly_payment = _format_currency(
        calc.get("monthly_kr")
        or calc.get("monthly_payment")
        or calc.get("monthly_amount")
    )
    total_interest = _format_currency(
        calc.get("total_interest_kr")
        or calc.get("total_interest")
        or calc.get("interest_sum")
    )

    rate = _coerce_float(calc.get("rate") or calc.get("annual_rate") or calc.get("apr"), default=0.0)
    term_years = _coerce_term_years(calc)
    repay_type = str(
        calc.get("repay_type")
        or calc.get("repayment_type")
        or calc.get("amortization_type")
        or "-"
    )

    rationale = str(
        calc.get("rationale")
        or calc.get("explanation")
        or "입력해주신 조건을 기준으로 계산한 결과입니다."
    )
    one_liner = str(
        calc.get("one_liner")
        or calc.get("summary")
        or "예상 한도와 상환 규모를 정리했어요."
    )
    assumptions = _normalize_assumptions(calc.get("assumptions"))

    sources = state.sources or [{"name": "계산 엔진", "date": "-"}]

    return {
        "mode": "calc",
        "limit_kr": limit,
        "rate": rate,
        "term_years": term_years,
        "repay_type": repay_type,
        "monthly_kr": monthly_payment,
        "total_interest_kr": total_interest,
        "rationale": rationale,
        "one_liner": one_liner,
        "assumptions": assumptions,
        "sources": sources,
    }


def _build_info_payload(state: OrchestrationState) -> dict[str, Any]:
    docs = state.docs or []
    sources = state.sources or _build_sources_from_docs(docs)

    if not docs:
        summary = "요청하신 정보를 정리했어요."
        details = "필요 시 지역/소득/규제 조건을 알려주면 더 정확히 설명할 수 있어요."
        logger.info("검색 결과가 없어 기본 안내 제공.")
    else:
        top_doc = docs[0]
        top_score = float(top_doc.get("score", 0.0))
        summary = _summarize_doc(top_doc, high_confidence=top_score >= _INFO_HIGH_CONFIDENCE)
        details = _compose_details(docs)

    return {
        "mode": "info",
        "summary": summary,
        "details": details,
        "sources": sources,
    }


def _coerce_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_term_years(calc: dict[str, Any]) -> float:
    if "term_years" in calc:
        try:
            years = float(calc["term_years"])
        except (TypeError, ValueError):
            return 0.0
        return _normalize_years(years)
    if "term_months" in calc:
        try:
            months = float(calc["term_months"])
            years = months / 12
        except (TypeError, ValueError):
            return 0.0
        return _normalize_years(years)
    return 0.0


def _normalize_years(years: float) -> float:
    rounded = round(years)
    if abs(years - rounded) < 1e-6:
        return int(rounded)
    return round(years, 2)


def _format_currency(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "-"
    return format(int(round(numeric)), ",")


def _normalize_assumptions(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(item) for item in raw if str(item).strip()]
    text = str(raw).strip()
    return [text] if text else []


def _build_sources_from_docs(docs: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for doc in docs:
        name = str(doc.get("source") or "자료 미상")
        date = str(doc.get("date") or "-")
        entry = {"name": name, "date": date}
        if entry not in sources:
            sources.append(entry)
    return sources[:5]


def _summarize_doc(doc: dict[str, Any], *, high_confidence: bool) -> str:
    summary = doc.get("summary") or doc.get("title") or doc.get("text") or ""
    summary = str(summary).strip()
    summary = summary or "확인된 정책과 요건을 정리했어요."
    if not high_confidence:
        return f"{summary}\n(신뢰도가 낮아 최신 정보를 다시 확인해주세요.)"
    return summary


def _compose_details(docs: list[dict[str, Any]]) -> str:
    snippets: list[str] = []
    for doc in docs[:3]:
        text = str(doc.get("text") or doc.get("content") or "").strip()
        if not text:
            continue
        snippets.append(f"- {text[:280]}")
    if not snippets:
        return "자료 요약을 준비 중입니다."
    return "\n".join(snippets)
