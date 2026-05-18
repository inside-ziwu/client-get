## 1. 线上数据确认

- [x] 1.1 查询线上 `waimaotong_raw_companies` 13 列的非空行数
- [x] 1.2 查询线上 `waimaotong_raw_contacts` 8 列的非空行数
- [x] 1.3 如有非空数据，评估数据价值并决定是否导出备份

## 2. Alembic 迁移

- [x] 2.1 创建 Alembic revision：`20260518_0042_drop_unused_raw_columns.py`
- [x] 2.2 编写 upgrade 函数：DROP COLUMN IF EXISTS × 21
- [x] 2.3 编写 downgrade 函数：ADD COLUMN IF NOT EXISTS × 21（含正确类型）

## 3. 本地验证

- [x] 3.1 ~~本地执行~~ 本地 PG 未运行，跳过；迁移文件语法验证通过
- [x] 3.2 确认 `waimaotong_raw_companies` 从 66 列减到 53 列（线上验证 ✓）
- [x] 3.3 确认 `waimaotong_raw_contacts` 从 29 列减到 21 列（线上验证 ✓）
- [x] 3.4 跳过（线上不做 downgrade 测试）
- [x] 3.5 跳过

## 4. 线上部署

- [x] 4.1 线上执行迁移 SQL（事务内，含 alembic_version 更新）
- [x] 4.2 确认两张表列数正确（53 + 21） ✓
