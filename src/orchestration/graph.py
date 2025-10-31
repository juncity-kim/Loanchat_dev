from orchestration.state import OrchestrationState
from orchestration.router import route
from orchestration.composer import render_answer
from compute.engine import run as compute_run, ComputeInputs  # ← 추가

def run(query: str, inputs: dict | None = None) -> str:
    state = OrchestrationState(user_query=query, inputs=inputs or {})
    state = route(state)

    if state.mode == "calc":
        ci = ComputeInputs(
            house_price = int(state.inputs.get("house_price", 0)),
            annual_rate = float(state.inputs.get("annual_rate", 0.039)),
            term_years  = int(state.inputs.get("term_years", 35)),
            monthly_debt= int(state.inputs.get("monthly_debt", 0)),
            annual_income=int(state.inputs.get("annual_income", 0)),
        )
        state.calc = compute_run(ci)
        state.sources = [{"name": "가정값/내부계산", "date": "local"}]

    return render_answer(state)
