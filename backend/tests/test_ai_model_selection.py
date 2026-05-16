import pytest

from app.core.errors import AppError
from app.services.intelligence_service import IntelligenceService
from app.services.scoring_service import ScoringService
from app.services.tenant_messaging_service import TenantMessagingService


class _Result:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def mappings(self) -> "_Result":
        return self

    def first(self) -> dict | None:
        return self._row


class _FallbackAvailableConnection:
    def __init__(self) -> None:
        self.statements: list[str] = []

    async def execute(self, statement, params=None) -> _Result:
        sql = str(statement)
        self.statements.append(sql)
        if len(self.statements) > 1:
            return _Result({"id": "fallback-model-id", "display_name": "Fallback Model"})
        return _Result(None)


async def test_scoring_model_selection_fails_without_scene_default() -> None:
    conn = _FallbackAvailableConnection()

    with pytest.raises(AppError) as exc_info:
        await ScoringService()._get_model(conn)  # noqa: SLF001

    assert exc_info.value.message == "当前没有可用评分模型"
    assert len(conn.statements) == 1


async def test_intelligence_model_selection_fails_without_scene_default() -> None:
    conn = _FallbackAvailableConnection()

    with pytest.raises(AppError) as exc_info:
        await IntelligenceService()._get_model(conn)  # noqa: SLF001

    assert exc_info.value.message == "当前没有可用情报模型"
    assert len(conn.statements) == 1


async def test_email_generation_model_selection_fails_without_scene_default() -> None:
    conn = _FallbackAvailableConnection()

    with pytest.raises(AppError) as exc_info:
        await TenantMessagingService()._get_ai_model_for_scene(conn, "email_generation")  # noqa: SLF001

    assert exc_info.value.message == "当前未配置可用 AI 模型"
    assert len(conn.statements) == 1
