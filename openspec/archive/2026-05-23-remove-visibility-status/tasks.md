## 1. 数据库迁移

- [ ] 1.1 新建 alembic 迁移：DROP CONSTRAINT tenant_companies_visibility_status_check → DROP INDEX idx_tenant_companies_tenant_visibility → DROP COLUMN visibility_status

## 2. 移除查询过滤

- [ ] 2.1 `tenant_query_service.py`：移除 dashboard_overview（:32-33）、companies_page（:182）、v3_company_detail（:453）、第二个列表方法（:598）共 4 处 visibility_status 过滤
- [ ] 2.2 `tenant_ops_service.py`：移除 :28、:46、:69、:97、:298、:674、:720、:1162 共 7 处过滤；create_company 的 INSERT（:208）去掉 visibility_status 列；`_assert_visible_tenant_company` 重命名为 `_assert_tenant_company_exists`，更新所有调用点
- [ ] 2.3 `tenant_messaging_service.py`：移除 :781、:2064、:2090、:2112、:2135 共 5 处过滤
- [ ] 2.4 `webhook_service.py`：移除 :133 的 1 处过滤

## 3. 简化 fan-out

- [ ] 3.1 `fan_out.py`：run_fan_out_for_tenant_keyword 的 INSERT 去掉 visibility_status 列，ON CONFLICT 去掉 SET visibility_status 和 WHERE 条件
- [ ] 3.2 `fan_out.py`：删除 hide_tenant_companies_for_cancelled_keyword 整个函数

## 4. 简化 wmt_lineage_repair

- [ ] 4.1 `wmt_lineage_repair.py`：_SQL_FAN_OUT_ACTIVE_KEYWORDS 去掉 visibility_status 列和 ON CONFLICT 中的相关设置
- [ ] 4.2 `wmt_lineage_repair.py`：_SQL_HIDE_STALE_RELATIONS 改为 DELETE（删除 clean_company_id 在 wmt 中已不存在的 tenant_companies）
- [ ] 4.3 `wmt_lineage_repair.py`：_SQL_VISIBLE_JOIN_COUNT 重命名并去掉 visibility 过滤

## 5. 关键词 CRUD 收口

- [ ] 5.1 `tenant_settings_service.py`：删除 hide_tenant_companies_for_cancelled_keyword 的 import
- [ ] 5.2 `tenant_settings_service.py`：update_keyword 去掉 hide 旧关键词的调用，只保留 fan-out 新关键词
- [ ] 5.3 `tenant_settings_service.py`：delete_keyword 去掉 hide 调用，只 soft-delete keyword 记录

## 6. 清理脚本

- [ ] 6.1 `rebuild_tenant_companies.py`：去掉 visibility_status 引用

## 7. 验证

- [ ] 7.1 迁移：本地执行 alembic upgrade head 成功，tenant_companies 表无 visibility_status 列
- [ ] 7.2 公司列表：tenant 端公司列表正常加载，数量与预期一致
- [ ] 7.3 关键词创建：新建关键词后 fan-out 正常，匹配公司出现在列表
- [ ] 7.4 关键词删除：删除关键词后 tenant_companies 不受影响，公司仍在列表
- [ ] 7.5 发送计划：创建计划 → 选群组 → 锁定收件人，收件人不为空
- [ ] 7.6 wmt_lineage_repair：手动触发一次，日志正常无报错
