"""/admin 라우터."""

from __future__ import annotations

from datetime import datetime, timezone

from datetime import datetime, timezone

from fastapi import APIRouter

from src.api.schemas import HealthResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])
from src.api.schemas import HealthResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get(
    "/health",
    response_model=HealthResponse,
    response_model_exclude_none=True,
    summary="관리자 헬스체크",
)
def read_health() -> HealthResponse:
    """기본 헬스체크 응답."""

    # TODO(Iteration 4): core.responses.ok() 적용하여 공통 포맷으로 반환 고려
    return HealthResponse(
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
    )
