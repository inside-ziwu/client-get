"""instance_id 和 JWT_SECRET 配置测试"""

import os
from unittest.mock import patch

import pytest


def _fresh_settings(**env_overrides):
    """清除 lru_cache 后用指定环境变量创建 Settings"""
    from app.core.config import get_settings

    get_settings.cache_clear()
    base = {
        "JWT_SECRET": "test-secret",
        "CLIENTGET_JWT_SECRET": "test-secret",
        "ADMIN_EMAIL": "a@b.com",
        "ADMIN_PASSWORD": "pw",
        "DATA_SOURCE_ENCRYPTION_KEY": "k" * 32,
        "INTERNAL_SERVICE_SECRET": "s",
        "ENGAGELAB_WEBHOOK_SECRET": "w",
        "APP_ENV": "local",
        "CLIENTGET_INSTANCE_ID": "",
    }
    base.update(env_overrides)
    # 移除空值
    base = {k: v for k, v in base.items() if v != ""}
    with patch.dict(os.environ, base, clear=True):
        get_settings.cache_clear()
        s = get_settings()
        get_settings.cache_clear()
        return s


class TestInstanceId:
    def test_default_value(self):
        s = _fresh_settings()
        assert s.instance_id == "default"

    def test_custom_value(self):
        s = _fresh_settings(CLIENTGET_INSTANCE_ID="instance_b")
        assert s.instance_id == "instance_b"

    def test_production_fail_fast_without_instance_id(self):
        with pytest.raises(Exception):
            _fresh_settings(APP_ENV="production")

    def test_production_ok_with_instance_id(self):
        s = _fresh_settings(APP_ENV="production", CLIENTGET_INSTANCE_ID="prod_a")
        assert s.instance_id == "prod_a"


class TestJwtSecret:
    def test_clientget_jwt_secret_takes_priority(self):
        s = _fresh_settings(CLIENTGET_JWT_SECRET="new-secret", JWT_SECRET="old-secret")
        assert s.jwt_secret == "new-secret"

    def test_jwt_secret_fallback(self):
        s = _fresh_settings(JWT_SECRET="old-secret", CLIENTGET_JWT_SECRET="")
        assert s.jwt_secret == "old-secret"
