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

    def test_production_ok_with_explicit_default(self):
        """Instance A 生产合法配置：显式设置 CLIENTGET_INSTANCE_ID=default（存量数据即 default）"""
        s = _fresh_settings(APP_ENV="production", CLIENTGET_INSTANCE_ID="default")
        assert s.instance_id == "default"


class TestCookieDomain:
    """refresh cookie Domain 按实例配置（COOKIE_DOMAIN），未设置时生产回退 .xinanpcb.com"""

    def _domain(self, **env):
        from unittest.mock import patch as _patch

        s = _fresh_settings(**env)
        from app.api.admin import auth as admin_auth

        with _patch.object(admin_auth, "get_settings", return_value=s):
            return admin_auth._cookie_domain()

    def test_explicit_cookie_domain_wins(self):
        assert (
            self._domain(
                APP_ENV="production",
                CLIENTGET_INSTANCE_ID="instance_b",
                COOKIE_DOMAIN=".instance-b.example.com",
            )
            == ".instance-b.example.com"
        )

    def test_production_fallback_keeps_instance_a_zero_config(self):
        assert (
            self._domain(APP_ENV="production", CLIENTGET_INSTANCE_ID="default")
            == ".xinanpcb.com"
        )

    def test_local_unset_returns_none(self):
        assert self._domain() is None


class TestJwtSecret:
    def test_clientget_jwt_secret_takes_priority(self):
        s = _fresh_settings(CLIENTGET_JWT_SECRET="new-secret", JWT_SECRET="old-secret")
        assert s.jwt_secret == "new-secret"

    def test_jwt_secret_fallback(self):
        s = _fresh_settings(JWT_SECRET="old-secret", CLIENTGET_JWT_SECRET="")
        assert s.jwt_secret == "old-secret"
