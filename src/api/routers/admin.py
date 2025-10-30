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
    description="서비스가 정상 동작 중인지 확인합니다.",
)
def read_health() -> HealthResponse:
    """기본 헬스체크 응답을 반환한다."""

    return HealthResponse(timestamp=datetime.now(timezone.utc))
