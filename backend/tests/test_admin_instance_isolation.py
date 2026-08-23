"""管理端平台配置 + Dashboard instance_id 隔离测试（U18-U23）

U17（platform_users）不在 admin_config_service.py 中，跳过。
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.admin_config_service import AdminConfigService

INSTANCE_ID = "test-instance"


def _mock_settings():
    s = MagicMock()
    s.instance_id = INSTANCE_ID
    return s


def _mock_mappings_all(rows: list[dict]):
    """构造 conn.execute 返回 mappings().all() 的 mock"""
    mappings = []
    for row in rows:
        m = MagicMock()
        m.__getitem__ = lambda self, key, _r=row: _r[key]
        m.get = lambda key, default=None, _r=row: _r.get(key, default)
        mappings.append(m)
    result = MagicMock()
    result.mappings.return_value.all.return_value = mappings
    return result


def _mock_mappings_first(row_dict):
    """构造 conn.execute 返回 mappings().first() 的 mock"""
    if row_dict is None:
        result = MagicMock()
        result.mappings.return_value.first.return_value = None
        result.first.return_value = None
        return result
    mapping = MagicMock()
    mapping.__getitem__ = lambda self, key, _r=row_dict: _r[key]
    mapping.get = lambda key, default=None, _r=row_dict: _r.get(key, default)
    result = MagicMock()
    result.mappings.return_value.first.return_value = mapping
    result.first.return_value = None
    return result


def _mock_mappings_one(row_dict):
    """构造 conn.execute 返回 mappings().one() 的 mock"""
    mapping = MagicMock()
    mapping.__getitem__ = lambda self, key, _r=row_dict: _r[key]
    mapping.get = lambda key, default=None, _r=row_dict: _r.get(key, default)
    result = MagicMock()
    result.mappings.return_value.one.return_value = mapping
    return result


def _extract_params(call):
    """从 conn.execute 调用中提取参数字典"""
    if len(call.args) > 1:
        return call.args[1]
    return call.kwargs


def _extract_sql(call):
    """从 conn.execute 调用中提取 SQL 字符串"""
    return str(call.args[0].text if hasattr(call.args[0], 'text') else call.args[0])


@pytest.fixture(autouse=True)
def _patch_settings():
    with patch("app.services.admin_config_service.get_settings", return_value=_mock_settings()):
        yield


# ── U18: warmup_rules ──────────────────────────────────────────────────────


class TestWarmupRulesInstanceId:
    """U18: warmup_rules CRUD 按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_list_warmup_rules_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=_mock_mappings_all([]))

        await svc.list_warmup_rules(conn)

        conn.execute.assert_called_once()
        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_put_warmup_rules_insert_contains_instance_id(self):
        """当没有 active 规则时，INSERT 包含 instance_id"""
        svc = AdminConfigService()
        conn = AsyncMock()

        now = datetime.now()
        # put_warmup_rules 内部先调用 list_warmup_rules:
        #   list_warmup_rules: SELECT warmup_rules → 空
        list_empty = _mock_mappings_all([])
        # INSERT warmup_rules
        insert_result = MagicMock()
        # put_warmup_rules 结尾再调用 list_warmup_rules:
        #   list_warmup_rules: SELECT warmup_rules → 1 行
        rule_row = {
            "id": "rule-001",
            "name": "默认规则",
            "is_active": True,
            "min_observation_emails": 20,
            "bounce_alert_rate": Decimal("0.05"),
            "config": {},
            "created_at": now,
            "updated_at": now,
        }
        list_after = _mock_mappings_all([rule_row])
        # list_warmup_rules 对每行调用 _list_warmup_rule_levels
        levels_empty = _mock_mappings_all([])

        conn.execute = AsyncMock(
            side_effect=[list_empty, insert_result, list_after, levels_empty]
        )

        svc.audit = MagicMock()
        svc.audit.write = AsyncMock()

        # 直接从 put_warmup_rules 入口 mock，只验证 INSERT 参数
        # 因为 list_warmup_rules 被调了两次，需要正确的 side_effect 顺序
        # 第一次 list_warmup_rules：空 → 触发 INSERT
        # INSERT warmup_rules
        # 第二次 list_warmup_rules (after): SELECT warmup_rules + _list_warmup_rule_levels
        # put_warmup_rules 中 rule_id 动态生成，所以第二次 list 需要返回匹配的 id
        # 为了避免 id 匹配问题，我们 mock new_uuid 使其返回固定值
        with patch("app.services.admin_config_service.new_uuid", return_value="rule-001"):
            await svc.put_warmup_rules(
                conn,
                payload={"name": "默认规则", "levels": []},
                platform_user_id="pu-001",
            )

        # 第 2 个调用：INSERT warmup_rules
        insert_call = conn.execute.call_args_list[1]
        params = _extract_params(insert_call)
        assert params["instance_id"] == INSTANCE_ID


# ── U19: platform_scoring_templates ────────────────────────────────────────


class TestPlatformScoringTemplatesInstanceId:
    """U19: platform_scoring_templates CRUD 按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_list_scoring_templates_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=_mock_mappings_all([]))

        await svc.list_platform_scoring_templates(conn)

        conn.execute.assert_called_once()
        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_list_scoring_templates_with_industry_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=_mock_mappings_all([]))

        await svc.list_platform_scoring_templates(conn, industry="electronics")

        conn.execute.assert_called_once()
        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID
        assert params["industry"] == "electronics"

    @pytest.mark.asyncio
    async def test_create_scoring_template_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        svc.audit = MagicMock()
        svc.audit.write = AsyncMock()

        now = datetime.now()
        template_row = {
            "id": "tmpl-001",
            "industry": "electronics",
            "name": "测试模板",
            "description": None,
            "is_active": True,
            "dimensions": [],
            "grade_thresholds": {"S": 90, "A": 80, "B": 60, "C": 40, "D": 0},
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }

        # INSERT platform_scoring_templates
        insert_result = MagicMock()
        # INSERT platform_scoring_template_versions
        version_result = MagicMock()
        # get_platform_scoring_template
        get_result = _mock_mappings_first(template_row)

        conn.execute = AsyncMock(side_effect=[insert_result, version_result, get_result])

        await svc.create_platform_scoring_template(
            conn,
            payload={
                "industry": "electronics",
                "name": "测试模板",
                "dimensions": [],
            },
            platform_user_id="pu-001",
        )

        # 第 1 个调用：INSERT platform_scoring_templates
        insert_call = conn.execute.call_args_list[0]
        params = _extract_params(insert_call)
        assert params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_get_scoring_template_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        now = datetime.now()
        template_row = {
            "id": "tmpl-001",
            "industry": "electronics",
            "name": "测试模板",
            "description": None,
            "is_active": True,
            "dimensions": [],
            "grade_thresholds": {},
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
        conn.execute = AsyncMock(return_value=_mock_mappings_first(template_row))

        await svc.get_platform_scoring_template(conn, "tmpl-001")

        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID
        assert params["template_id"] == "tmpl-001"

    @pytest.mark.asyncio
    async def test_delete_scoring_template_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=MagicMock())

        await svc.delete_platform_scoring_template(conn, "tmpl-001")

        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID
        assert params["id"] == "tmpl-001"


# ── U20: platform_email_templates ──────────────────────────────────────────


class TestPlatformEmailTemplatesInstanceId:
    """U20: platform_email_templates CRUD 按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_list_email_templates_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=_mock_mappings_all([]))

        await svc.list_platform_email_templates(conn)

        conn.execute.assert_called_once()
        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_create_email_template_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        svc.audit = MagicMock()
        svc.audit.write = AsyncMock()

        now = datetime.now()
        template_row = {
            "id": "et-001",
            "industry": "electronics",
            "name": "邮件模板",
            "description": None,
            "category": "default",
            "subject": "主题",
            "body_html": "<p>正文</p>",
            "body_text": "正文",
            "variables": [],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        insert_result = MagicMock()
        get_result = _mock_mappings_first(template_row)

        conn.execute = AsyncMock(side_effect=[insert_result, get_result])

        await svc.create_platform_email_template(
            conn,
            payload={
                "industry": "electronics",
                "name": "邮件模板",
                "subject": "主题",
                "body_html": "<p>正文</p>",
                "body_text": "正文",
            },
            platform_user_id="pu-001",
        )

        # 第 1 个调用：INSERT
        insert_call = conn.execute.call_args_list[0]
        params = _extract_params(insert_call)
        assert params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_get_email_template_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        now = datetime.now()
        template_row = {
            "id": "et-001",
            "industry": "electronics",
            "name": "邮件模板",
            "description": None,
            "category": "default",
            "subject": "主题",
            "body_html": "<p>正文</p>",
            "body_text": "正文",
            "variables": [],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        conn.execute = AsyncMock(return_value=_mock_mappings_first(template_row))

        await svc.get_platform_email_template(conn, "et-001")

        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_delete_email_template_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        svc.audit = MagicMock()
        svc.audit.write = AsyncMock()

        now = datetime.now()
        template_row = {
            "id": "et-001",
            "industry": "electronics",
            "name": "邮件模板",
            "description": None,
            "category": "default",
            "subject": "主题",
            "body_html": "<p>正文</p>",
            "body_text": "正文",
            "variables": [],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        # get_platform_email_template（before）
        get_result = _mock_mappings_first(template_row)
        # DELETE
        delete_result = MagicMock()

        conn.execute = AsyncMock(side_effect=[get_result, delete_result])

        await svc.delete_platform_email_template(
            conn, template_id="et-001", platform_user_id="pu-001"
        )

        # 第 2 个调用：DELETE
        delete_call = conn.execute.call_args_list[1]
        params = _extract_params(delete_call)
        assert params["instance_id"] == INSTANCE_ID


# ── U21: ai_models / ai_scene_defaults ─────────────────────────────────────


class TestAiModelsInstanceId:
    """U21: ai_models CRUD 按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_list_ai_models_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=_mock_mappings_all([]))

        await svc.list_ai_models(conn)

        conn.execute.assert_called_once()
        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_create_ai_model_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        svc.audit = MagicMock()
        svc.audit.write = AsyncMock()

        now = datetime.now()
        model_row = {
            "id": "m-001",
            "provider": "openrouter",
            "model_id": "gpt-4",
            "display_name": "GPT-4",
            "is_active": True,
            "config": {},
            "created_at": now,
            "updated_at": now,
        }
        insert_result = MagicMock()
        get_result = _mock_mappings_first(model_row)

        conn.execute = AsyncMock(side_effect=[insert_result, get_result])

        await svc.create_ai_model(
            conn,
            payload={"model_id": "gpt-4", "display_name": "GPT-4"},
            platform_user_id="pu-001",
        )

        # 第 1 个调用：INSERT
        insert_call = conn.execute.call_args_list[0]
        params = _extract_params(insert_call)
        assert params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_get_ai_model_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        now = datetime.now()
        model_row = {
            "id": "m-001",
            "provider": "openrouter",
            "model_id": "gpt-4",
            "display_name": "GPT-4",
            "is_active": True,
            "config": {},
            "created_at": now,
            "updated_at": now,
        }
        conn.execute = AsyncMock(return_value=_mock_mappings_first(model_row))

        await svc.get_ai_model(conn, "m-001")

        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_delete_ai_model_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        svc.audit = MagicMock()
        svc.audit.write = AsyncMock()

        now = datetime.now()
        model_row = {
            "id": "m-001",
            "provider": "openrouter",
            "model_id": "gpt-4",
            "display_name": "GPT-4",
            "is_active": True,
            "config": {},
            "created_at": now,
            "updated_at": now,
        }
        # scene_defaults 检查：无引用
        scene_check = MagicMock()
        scene_check.first.return_value = None
        # get_ai_model（before）
        get_result = _mock_mappings_first(model_row)
        # DELETE
        delete_result = MagicMock()

        conn.execute = AsyncMock(side_effect=[scene_check, get_result, delete_result])

        await svc.delete_ai_model(conn, model_id="m-001", platform_user_id="pu-001")

        # 第 1 个调用：scene_defaults 检查包含 instance_id
        scene_call = conn.execute.call_args_list[0]
        params = _extract_params(scene_call)
        assert params["instance_id"] == INSTANCE_ID

        # 第 3 个调用：DELETE ai_models 包含 instance_id
        delete_call = conn.execute.call_args_list[2]
        params = _extract_params(delete_call)
        assert params["instance_id"] == INSTANCE_ID


class TestAiSceneDefaultsInstanceId:
    """U21: ai_scene_defaults CRUD 按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_list_ai_scene_defaults_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=_mock_mappings_all([]))

        await svc.list_ai_scene_defaults(conn)

        conn.execute.assert_called_once()
        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_put_ai_scene_defaults_insert_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()
        svc.audit = MagicMock()
        svc.audit.write = AsyncMock()

        # model_check
        model_check = MagicMock()
        model_mapping = MagicMock()
        model_mapping.__getitem__ = lambda self, key: {"is_active": True}[key]
        model_check.mappings.return_value.first.return_value = model_mapping
        # existing check：scene 不存在
        existing_check = MagicMock()
        existing_check.mappings.return_value.first.return_value = None
        # INSERT
        insert_result = MagicMock()
        # list_ai_scene_defaults（after）
        list_after = _mock_mappings_all([])

        conn.execute = AsyncMock(
            side_effect=[model_check, existing_check, insert_result, list_after]
        )

        await svc.put_ai_scene_defaults(
            conn,
            payload=[{"scene": "email_write", "model_id": "m-001"}],
            platform_user_id="pu-001",
        )

        # model_check 包含 instance_id
        check_call = conn.execute.call_args_list[0]
        params = _extract_params(check_call)
        assert params["instance_id"] == INSTANCE_ID

        # existing check 包含 instance_id
        exist_call = conn.execute.call_args_list[1]
        params = _extract_params(exist_call)
        assert params["instance_id"] == INSTANCE_ID

        # INSERT 包含 instance_id
        insert_call = conn.execute.call_args_list[2]
        params = _extract_params(insert_call)
        assert params["instance_id"] == INSTANCE_ID








# ── U23: get_platform_dashboard ────────────────────────────────────────────


class TestPlatformDashboardInstanceId:
    """U23: get_platform_dashboard 统计查询按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_dashboard_contains_instance_id(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        dashboard_row = {
            "active_tenants": 5,
            "total_users": 20,
            "running_sending_plans": 3,
            "configured_openrouter_tenants": 2,
        }
        conn.execute = AsyncMock(return_value=_mock_mappings_one(dashboard_row))

        result = await svc.get_platform_dashboard(conn)

        conn.execute.assert_called_once()
        params = _extract_params(conn.execute.call_args)
        assert params["instance_id"] == INSTANCE_ID

        # 确认返回值正确
        assert result["active_tenants"] == 5
        assert result["total_users"] == 20

    @pytest.mark.asyncio
    async def test_dashboard_sql_contains_instance_id_filter(self):
        """验证 SQL 中包含 instance_id 过滤条件"""
        svc = AdminConfigService()
        conn = AsyncMock()

        dashboard_row = {
            "active_tenants": 0,
            "total_users": 0,
            "running_sending_plans": 0,
            "configured_openrouter_tenants": 0,
        }
        conn.execute = AsyncMock(return_value=_mock_mappings_one(dashboard_row))

        await svc.get_platform_dashboard(conn)

        sql = _extract_sql(conn.execute.call_args)
        assert "instance_id" in sql
