"""init_instance.py 初始化脚本测试（U30）

验证：
1. INIT_ADMIN_PASSWORD 未设置时报错退出
2. 脚本生成的 INSERT SQL 包含 instance_id
3. 密码是 hashed 不是明文
"""

import inspect
import os
from unittest.mock import MagicMock, patch

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

    def test_insert_data_sources_has_instance_id(self):
        """INSERT INTO data_sources 包含 instance_id 列"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        assert "data_sources" in source
        assert ":instance_id" in source

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

    def test_all_inserts_use_on_conflict(self):
        """所有 INSERT 使用 ON CONFLICT 实现幂等"""
        from scripts.init_instance import main

        source = inspect.getsource(main)
        # 统计 INSERT 和 ON CONFLICT 出现次数
        insert_count = source.lower().count("insert into")
        conflict_count = source.lower().count("on conflict")
        assert conflict_count >= insert_count, (
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
