from __future__ import annotations

from src.orchestration.composer import render_answer
from src.orchestration.state import OrchestrationState


def test_render_answer_info_with_high_confidence() -> None:
    state = OrchestrationState(
        user_query="전세 대출 요건 알려줘",
        mode="info",
        docs=[
            {
                "score": 0.82,
                "text": "전세자금대출은 임차보증금의 80% 한도로 지원됩니다.",
                "source": "금융위원회",
                "date": "2024-01-15",
            }
        ],
        sources=[{"name": "금융위원회", "date": "2024-01-15"}],
    )

    rendered = render_answer(state)

    assert "금융위원회" in rendered
    assert "전세자금대출은 임차보증금" in rendered
    assert "요약" in rendered


def test_render_answer_info_with_low_confidence_adds_caution() -> None:
    state = OrchestrationState(
        user_query="모기지 대출 규제?",
        mode="info",
        docs=[
            {
                "score": 0.6,
                "summary": "투기과열지구는 담보인정비율이 40%까지 제한됩니다.",
                "source": "국토교통부",
                "date": "2023-11-30",
            }
        ],
    )

    rendered = render_answer(state)

    assert "투기과열지구는 담보인정비율" in rendered
    assert "신뢰도가 낮아" in rendered


def test_render_answer_calc_formats_numbers_and_fields() -> None:
    state = OrchestrationState(
        user_query="한도 계산해줘",
        mode="calc",
        calc={
            "limit": 354_000_000,
            "monthly_payment": 1_200_000.45,
            "total_interest": 54_200_000.8,
            "rate": 0.0325,
            "term_years": 30,
            "repay_type": "원리금균등",
            "rationale": "연소득과 기존 부채를 반영한 산출값입니다.",
            "one_liner": "30년 원리금균등 상환 기준입니다.",
            "assumptions": ["금리 3.25%", "DSR 40% 제한"],
        },
        sources=[{"name": "계산 엔진", "date": "2024-05-01"}],
    )

    rendered = render_answer(state)

    assert "354,000,000원" in rendered
    assert "1,200,000원" in rendered
    assert "54,200,001원" in rendered  # 반올림 결과 확인
    assert "원리금균등" in rendered
    assert "30년(360개월)" in rendered
    assert "연소득과 기존 부채" in rendered
    assert "30년 원리금균등 상환" in rendered
