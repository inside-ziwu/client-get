"""创建租户发件域名预热初始化测试（change: fix-tenant-warmup-level-hardcode）

档位以当前实例激活预热规则（warmup_rules + warmup_rule_levels）为准：
- 档位存在 → 写入真实 daily_limit / warmup_rule_id
- 档位不存在或无激活规则 → 422，整体回滚
- 无 sender_domain → 不做档位查询
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.tenants import TenantCreateRequest
from app.services.tenant_service import TenantService

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
        m.__getitem__ = lambda self, key: row[key]  # noqa: B023
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
    mapping.__getitem__ = lambda self, key: row_dict[key]
    mapping.get = lambda key, default=None, _r=row_dict: _r.get(key, default)
    result = MagicMock()
    result.mappings.return_value.first.return_value = mapping
    result.first.return_value = None  # slug 查重返回 None
    return result


def _tenant_row(**overrides):
    now = datetime.now()
    base = {
        "id": "t-001",
        "name": "测试租户",
        "slug": "test",
        "industry": "electronics",
        "status": "active",
        "needs_onboarding": False,
        "contact_name": "张三",
        "contact_phone": "13800138000",
        "contact_email": "test@example.com",
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


def _create_payload(**overrides):
    base = {
        "name": "新租户",
        "slug": "new-tenant",
        "industry": "electronics",
        "admin_email": "admin@test.com",
        "admin_password": "pass1234",
        "admin_name": "管理员",
    }
    base.update(overrides)
    return base


def _bootstrap_side_effects():
    """create_tenant 在预热初始化之前的固定 execute 序列（与 U16 一致）：
    slug 查重 → INSERT tenants/users/user_roles → 评分模板 SELECT（空，走默认分支两次 INSERT）
    → 邮件模板 SELECT（空） → INSERT contact_rules
    """
    slug_check = MagicMock()
    slug_check.first.return_value = None
    return [
        slug_check,
        MagicMock(),  # INSERT tenants
        MagicMock(),  # INSERT users
        MagicMock(),  # INSERT user_roles
        _mock_mappings_first(None),  # 评分模板 SELECT
        MagicMock(),  # INSERT scoring_templates
        MagicMock(),  # INSERT scoring_template_versions
        _mock_mappings_all([]),  # 邮件模板 SELECT
        MagicMock(),  # INSERT contact_rules
    ]


@pytest.fixture(autouse=True)
def _patch_settings():
    with patch("app.services.tenant_service.get_settings", return_value=_mock_settings()):
        yield


class TestCreateTenantWarmupLevelValidation:
    """档位对照当前实例激活预热规则校验"""

    @pytest.mark.asyncio
    async def test_high_level_uses_real_daily_limit(self):
        """档位存在（19 档规则的 7 档）→ 写入真实 daily_limit / warmup_rule_id"""
        svc = TenantService()
        conn = AsyncMock()

        level_select = _mock_mappings_first({"rule_id": "rule-001", "daily_limit": 8000})
        conn.execute = AsyncMock(
            side_effect=[
                *_bootstrap_side_effects(),
                level_select,  # 档位查询
                MagicMock(),  # INSERT domain_warmup_status
                _mock_mappings_first(_tenant_row()),  # get_tenant
            ]
        )

        with patch("app.services.tenant_service.hash_password", return_value="hashed"):
            await svc.create_tenant(
                conn,
                platform_user_id="pu-001",
                payload=_create_payload(sender_domain="mail.example.com", warmup_level=7),
            )

        # 第 10 个调用：档位查询按当前实例 + 激活规则 + 档位过滤
        level_params = conn.execute.call_args_list[9].args[1]
        assert level_params["instance_id"] == INSTANCE_ID
        assert level_params["warmup_level"] == 7

        # 第 11 个调用：INSERT domain_warmup_status 用档位表真实值
        insert_params = conn.execute.call_args_list[10].args[1]
        assert insert_params["domain"] == "mail.example.com"
        assert insert_params["warmup_level"] == 7
        assert insert_params["daily_limit"] == 8000
        assert insert_params["warmup_rule_id"] == "rule-001"

    @pytest.mark.asyncio
    async def test_lowest_level_uses_rule_value_not_hardcode(self):
        """边界：1 档（缺省档位）日限取档位表值，而非硬编码映射"""
        svc = TenantService()
        conn = AsyncMock()

        # 档位表 1 档日限 80（与旧硬编码 50 不同，验证取的是表值）
        level_select = _mock_mappings_first({"rule_id": "rule-001", "daily_limit": 80})
        conn.execute = AsyncMock(
            side_effect=[
                *_bootstrap_side_effects(),
                level_select,
                MagicMock(),
                _mock_mappings_first(_tenant_row()),
            ]
        )

        with patch("app.services.tenant_service.hash_password", return_value="hashed"):
            await svc.create_tenant(
                conn,
                platform_user_id="pu-001",
                payload=_create_payload(sender_domain="mail.example.com", warmup_level=1),
            )

        insert_params = conn.execute.call_args_list[10].args[1]
        assert insert_params["daily_limit"] == 80

    @pytest.mark.asyncio
    async def test_missing_level_raises_422_without_insert(self):
        """档位在激活规则中不存在（99）→ 422，且不执行 domain_warmup_status INSERT"""
        svc = TenantService()
        conn = AsyncMock()

        conn.execute = AsyncMock(
            side_effect=[
                *_bootstrap_side_effects(),
                _mock_mappings_first(None),  # 档位查询无结果
            ]
        )

        with (
            patch("app.services.tenant_service.hash_password", return_value="hashed"),
            pytest.raises(AppError) as exc_info,
        ):
            await svc.create_tenant(
                conn,
                platform_user_id="pu-001",
                payload=_create_payload(sender_domain="mail.example.com", warmup_level=99),
            )

        assert exc_info.value.code == "VALIDATION_ERROR"
        assert exc_info.value.status_code == 422
        # 档位查询是最后一次 execute，之后无 INSERT / get_tenant
        assert conn.execute.call_count == 10

    @pytest.mark.asyncio
    async def test_no_active_rule_raises_422(self):
        """当前实例无激活预热规则 → 档位查询同样无结果 → 422"""
        svc = TenantService()
        conn = AsyncMock()

        conn.execute = AsyncMock(
            side_effect=[
                *_bootstrap_side_effects(),
                _mock_mappings_first(None),  # 无激活规则时查询无结果
            ]
        )

        with (
            patch("app.services.tenant_service.hash_password", return_value="hashed"),
            pytest.raises(AppError) as exc_info,
        ):
            await svc.create_tenant(
                conn,
                platform_user_id="pu-001",
                payload=_create_payload(sender_domain="mail.example.com", warmup_level=1),
            )

        assert exc_info.value.code == "VALIDATION_ERROR"
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_without_sender_domain_skips_warmup_query(self):
        """sender_domain 为空 → 不做档位查询、不写 domain_warmup_status"""
        svc = TenantService()
        conn = AsyncMock()

        conn.execute = AsyncMock(
            side_effect=[
                *_bootstrap_side_effects(),
                _mock_mappings_first(_tenant_row()),  # get_tenant
            ]
        )

        with patch("app.services.tenant_service.hash_password", return_value="hashed"):
            await svc.create_tenant(
                conn,
                platform_user_id="pu-001",
                payload=_create_payload(warmup_level=3),
            )

        # 固定 9 次 bootstrap + 1 次 get_tenant，无档位查询与预热 INSERT
        assert conn.execute.call_count == 10
        all_sql = " ".join(str(call.args[0]) for call in conn.execute.call_args_list)
        assert "warmup" not in all_sql


class TestTenantCreateRequestWarmupLevelSchema:
    """请求 schema 不再固定档位上限"""

    def test_level_7_passes_schema(self):
        req = TenantCreateRequest(
            **_create_payload(sender_domain="mail.example.com", warmup_level=7)
        )
        assert req.warmup_level == 7

    def test_level_0_rejected_by_schema(self):
        with pytest.raises(ValidationError):
            TenantCreateRequest(
                **_create_payload(sender_domain="mail.example.com", warmup_level=0)
            )
