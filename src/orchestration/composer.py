# orchestration/composer.py
# 템플릿을 이용해 최종 응답을 생성

from pathlib import Path
from jinja2 import Template
from orchestration.state import OrchestrationState

# prompts 디렉터리: 프로젝트 루트/ prompts 기준 (배포 안정)
PROMPTS = Path(__file__).resolve().parents[2] / "prompts"

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

def _load_template() -> Template:
    path = PROMPTS / "composer_answer.txt"
    if path.exists():
        return Template(path.read_text(encoding="utf-8"))
    return Template(_FALLBACK)

def render_answer(state: OrchestrationState) -> str:
    t = _load_template()
    if state.mode == "calc":
        return t.render(
            mode="calc",
            limit_kr=state.calc.get("limit_kr", "-"),
            rate=state.calc.get("rate", "-"),
            term_years=state.calc.get("term_years", "-"),
            repay_type=state.calc.get("repay_type", "-"),
            sources=state.sources or [],
        )
    return t.render(
        mode="info",
        summary="요청하신 정보를 정리했어요.",
        details="필요 시 지역/소득/규제 조건을 알려주면 더 정확히 설명해.",
        sources=state.sources or [],
    )
