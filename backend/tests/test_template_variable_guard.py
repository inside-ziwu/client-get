"""模板未知变量 422 防线：锁定收件人 / 启动计划前拦截无法替换的 {{...}}。

背景：2026-07-07 生产事故——模板含 {{First Name}}（外部工具风格变量），
渲染精确 replace 不认识，1275 封邮件以字面量发出。
"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import AppError
from app.services.tenant_messaging_service import TenantMessagingService


def _conn_with_templates(rows: list[dict]) -> AsyncMock:
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
    conn = AsyncMock()
    conn.execute.return_value = result
    return conn


def _tpl(name="模板A", subject="Hi {{contact_name}}", body_html="<p>{{company_name}}</p>", body_text=""):
    return {"name": name, "subject": subject, "body_html": body_html, "body_text": body_text}


class TestValidatePlanTemplateVariables:
    @pytest.mark.asyncio
    async def test_known_variables_pass(self):
        conn = _conn_with_templates(
            [_tpl(body_text="{{company_name}} {{contact_name}} {{contact_email}} {{sender_name}}")]
        )
        await TenantMessagingService()._validate_plan_template_variables(conn, "t-1", "p-1")

    @pytest.mark.asyncio
    async def test_foreign_style_variable_blocked(self):
        conn = _conn_with_templates([_tpl(body_text="Hi {{First Name}},")])
        with pytest.raises(AppError) as exc:
            await TenantMessagingService()._validate_plan_template_variables(conn, "t-1", "p-1")
        assert exc.value.code == "UNKNOWN_TEMPLATE_VARIABLES"
        assert exc.value.status_code == 422
        assert "{{First Name}}" in exc.value.message
        assert "模板A" in exc.value.message

    @pytest.mark.asyncio
    async def test_padded_known_variable_blocked(self):
        # 渲染是精确 replace，{{ company_name }} 带空格同样替换不了，必须拦
        conn = _conn_with_templates([_tpl(subject="{{ company_name }}")])
        with pytest.raises(AppError) as exc:
            await TenantMessagingService()._validate_plan_template_variables(conn, "t-1", "p-1")
        assert "{{ company_name }}" in exc.value.message

    @pytest.mark.asyncio
    async def test_multiple_templates_aggregated(self):
        conn = _conn_with_templates(
            [
                _tpl(name="模板A", body_text="{{foo}}"),
                _tpl(name="模板B", subject="{{bar}} {{foo}}"),
            ]
        )
        with pytest.raises(AppError) as exc:
            await TenantMessagingService()._validate_plan_template_variables(conn, "t-1", "p-1")
        for token in ("模板A", "模板B", "{{foo}}", "{{bar}}"):
            assert token in exc.value.message

    @pytest.mark.asyncio
    async def test_empty_plan_passes(self):
        conn = _conn_with_templates([])
        await TenantMessagingService()._validate_plan_template_variables(conn, "t-1", "p-1")


class TestGuardWiredIntoEntrypoints:
    def test_start_plan_and_lock_recipients_call_guard(self):
        for method in (TenantMessagingService.start_plan, TenantMessagingService.lock_plan_recipients):
            assert "_validate_plan_template_variables" in inspect.getsource(method), method.__name__

    def test_claim_render_mapping_covers_known_variables(self):
        # 发送渲染 mapping 必须覆盖 KNOWN_TEMPLATE_VARIABLES 全集（否则守卫放行的变量发不出来）
        source = inspect.getsource(TenantMessagingService.claim_due_emails)
        for var in TenantMessagingService.KNOWN_TEMPLATE_VARIABLES:
            assert f'"{var}"' in source, var
