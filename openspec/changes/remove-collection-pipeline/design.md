## Context

采集→清洗→评分管道将全面重写，当前代码不再使用。代码引用了 raw 表上的 CG 原生列，阻碍数据库清理。本次先删代码、断 import 链，再删列。

`admin_collection_service.py` 保留（管理端数据查看），但其 SQL 中引用了部分即将删除的列，需同步修改。

## Goals / Non-Goals

**Goals:**
- 删除全部管道代码，确保 FastAPI 主进程正常启动
- 断开 import 链，不留悬空引用
- 删除 raw 表上不再被引用的 CG 原生列
- 保留管理端数据查看能力

**Non-Goals:**
- 不重写管道
- 不删除数据库表
- 不影响租户端功能

## Decisions

### D1: 分两步执行——先删代码，再删列

**选择**：第一步删文件+改 import 链，确认后端能启动；第二步再写 Alembic revision 删列。

**理由**：解耦风险。代码删错可以 git revert，列删错需要从备份恢复。分步执行便于定位问题。

### D2: integrations/collection/ 整目录删除

**选择**：删除整个 `integrations/collection/` 目录（waimaotong.py + lixiaoyun.py + tendata.py + base.py + router.py）。

**替代方案**：只删 waimaotong.py，保留其他 provider。

**理由**：删掉 `workers/collection.py` 后，整个目录不再有运行时引用者。留着是死代码。

### D3: admin/collection.py 路由保留还是删除

**选择**：保留 `admin_collection_service.py`，但删除 `api/admin/collection.py`（路由层）中的采集触发/停止/重置端点，只保留数据查看端点。

**修正**：经分析，`api/admin/collection.py` 中触发/查看功能混在一起。保留整个文件和路由注册，只需修改 `admin_collection_service.py` 中引用被删列的 SQL。

### D4: admin_collection_service.py 的 SQL 修改策略

**选择**：在 `list_v3_raw_companies()` 等函数中，移除 SELECT 和 WHERE 中引用被删列的字段（约 1277-1294 行的 waimaotong 分支）。

**理由**：这些列删除后 SQL 会报错。管理端查看功能使用剩余列即可。

### D5: waimaotong_raw_companies 删除哪 20 列

删除 0035 迁移的原生设计列中，不在原项目 company_data + company_detail 中出现的列：

`keyword_master_id`, `collection_type`, `source_id`, `country_iso3`, `address`, `emails`, `trade_amount_3y_usd`, `trade_count`, `has_trade_data`, `customs_data`, `search_payload`, `detail_payload`, `trade_payload`, `raw_payload`, `detail_fetched_at`, `trade_status`, `trade_fetched_at`, `contacts_status`, `contacts_fetched_at`, `enrichment_error`

删除后 raw_companies 从 53 列减到 33 列。

### D6: waimaotong_raw_contacts 兼容列保留

**决定**：保留 `sys_contact_id`, `contact_id`, `sys_company_id`, `api_company_id`, `company_id` 这 5 列。

**理由**：这些列与原项目 contact_data 的结构保持一致，未来重写管道时写入数据需要和原项目逻辑一致。raw_contacts 维持 21 列不变。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 管理端前端调用被删端点 404 | 采集触发/停止端点在 admin 前端可能有对应按钮，删后按钮 404。可接受，前端后续适配 |
| 管理端 SQL 改错导致数据查看崩溃 | 修改后本地验证 SQL 语法；线上部署后立即验证管理端页面 |
| 列删除后数据丢失 | 上一个 change 已备份 13+8 列数据；本次 20+5 列同样先查非空行数、导出备份 |
| 重写时缺少参考代码 | git 历史保留全部删除记录，可随时回溯 |
