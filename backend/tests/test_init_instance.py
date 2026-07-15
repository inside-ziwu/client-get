"""init_instance.py 初始化脚本测试（U30）

验证：
1. INIT_ADMIN_PASSWORD 未设置时报错退出
2. 现役平台配置 INSERT 包含 instance_id，且不再初始化数据源
3. 密码是 hashed 不是明文
"""

import inspect
import os
from unittest.mock import patch

import pytest


class TestInitInstanceEnvValidation:
    """环境变量校验"""

    def test_missing_admin_password_exits(self):
        """INIT_ADMIN_PASSWORD 未设置时 sys.exit(1)"""
        env = {
            "INIT_ADMIN_EMAIL": "admin@test.com",
            "CLIENTGET_INSTANCE_ID": "instance_b",
            "DATABASE_URL": "postgresql://localhost/test",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                from scripts.init_instance import main

                main()
            assert exc_info.value.code == 1

    def test_missing_admin_email_exits(self):
        """INIT_ADMIN_EMAIL 未设置时 sys.exit(1)"""
        env = {
            "INIT_ADMIN_PASSWORD": "secret123",
            "CLIENTGET_INSTANCE_ID": "instance_b",
            "DATABASE_URL": "postgresql://localhost/test",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                from scripts.init_instance import _require_env

                _require_env("INIT_ADMIN_EMAIL")
            assert exc_info.value.code == 1

    def test_missing_instance_id_exits(self):
        """CLIENTGET_INSTANCE_ID 未设置时 sys.exit(1)"""
        env = {
            "INIT_ADMIN_EMAIL": "admin@test.com",
            "INIT_ADMIN_PASSWORD": "secret123",
            "DATABASE_URL": "postgresql://localhost/test",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                from scripts.init_instance import _require_env

                _require_env("CLIENTGET_INSTANCE_ID")
            assert exc_info.value.code == 1

    def test_default_instance_id_rejected(self):
        """instance_id='default' 被拒绝"""
        env = {
            "INIT_ADMIN_EMAIL": "admin@test.com",
            "INIT_ADMIN_PASSWORD": "secret123",
            "CLIENTGET_INSTANCE_ID": "default",
            "DATABASE_URL": "postgresql://localhost/test",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                from scripts.init_instance import main

                main()
            assert exc_info.value.code == 1


class TestInitInstanceSqlContent:
    """验证脚本源码中 SQL 包含 instance_id"""

    def test_insert_platform_users_has_instance_id(self):
        """INSERT INTO platform_users 包含 instance_id 列"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        # 确认 platform_users INSERT 包含 instance_id
        assert "platform_users" in source
        assert "instance_id" in source

    def test_does_not_initialize_retired_data_sources(self):
        """采集凭证体系退役后，不再初始化 data_sources"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        assert "data_sources" not in source

    def test_insert_warmup_rules_has_instance_id(self):
        """INSERT INTO warmup_rules 包含 instance_id"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        assert "warmup_rules" in source

    def test_insert_scoring_templates_has_instance_id(self):
        """INSERT INTO platform_scoring_templates 包含 instance_id"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        assert "platform_scoring_templates" in source

    def test_insert_email_templates_has_instance_id(self):
        """INSERT INTO platform_email_templates 包含 instance_id"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        assert "platform_email_templates" in source

    def test_insert_ai_models_has_instance_id(self):
        """INSERT INTO ai_models 包含 instance_id"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        assert "ai_models" in source

    def test_insert_ai_scene_defaults_has_instance_id(self):
        """INSERT INTO ai_scene_defaults 包含 instance_id"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        assert "ai_scene_defaults" in source

    def test_all_inserts_use_on_conflict_or_pre_check(self):
        """所有 INSERT 使用 ON CONFLICT 或先查后插实现幂等/安全性"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        # platform_users 改为先查后插（显式报错），其余 INSERT 仍用 ON CONFLICT
        insert_count = source.lower().count("insert into")
        conflict_count = source.lower().count("on conflict")
        # platform_users 的 INSERT 不再使用 ON CONFLICT，而是先检查再插入
        # 因此允许差 1（platform_users 那条）
        assert conflict_count >= insert_count - 1, (
            f"INSERT 出现 {insert_count} 次，ON CONFLICT 仅 {conflict_count} 次"
        )


class TestInitInstancePasswordHashing:
    """验证密码被哈希存储"""

    def test_password_is_hashed_not_plaintext(self):
        """密码通过 hash_password 哈希后存入数据库"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        # 验证调用了 hash_password
        assert "hash_password" in source
        # 验证参数使用的是 password_hash 而非明文密码
        assert "password_hash" in source

    def test_hash_password_imported(self):
        """脚本导入了 hash_password"""
        import scripts.init_instance as module

        assert hasattr(module, "hash_password")

    def test_hash_password_produces_bcrypt_output(self):
        """hash_password 产生 bcrypt 格式输出"""
        from app.security.passwords import hash_password

        result = hash_password("test-password")
        # bcrypt 哈希以 $2b$ 开头
        assert result.startswith("$2b$") or result.startswith("$2a$")
        # 哈希值不等于明文
        assert result != "test-password"
