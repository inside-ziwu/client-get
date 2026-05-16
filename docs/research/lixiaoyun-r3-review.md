# R-3 励销云 Provider 接口审查报告

**日期**: 2026-04-30  
**对象**: `backend/app/integrations/collection/lixiaoyun.py`（367 行）  
**审查目标**: 复核现有实现是否满足 Phase 1 腾道反推 Stage 1 需求（关键词 → 中国 PCB 同行 → 英文名）

---

## 1. Stage 1 需求清单（来自 spec v1.3）

| 需求 | 描述 |
|---|---|
| 输入 | 关键词字符串（如 "PCB"） |
| 核心输出 | 中国 PCB 同行公司**英文名列表**（喂给腾道 T1 Search 的 `keyword`） |
| 富集 | 同行公司基础信息（地址/法人/规模/统一信用代码等） |
| 配额 | 30 同行 / 关键词 / 天（可配置） |
| 跨天恢复 | 续跑未采集完的同行索引 |
| 落库 | `lixiaoyun_raw_companies` 渠道专表（仅 Admin 可见，不进入 clean） |
| 失败处理 | 401 → 凭证失效；429 → 限流退避；单公司失败不阻塞 |
| 回调集成 | `on_partial`（搜索完成）+ `on_company_enriched`（单公司富集完成） |

---

## 2. 现状能力（已具备 ✅）

| # | 能力 | 实现 |
|---|---|---|
| 1 | 关键词搜索 + 分页 | `POST /api_skb/v1/search`，`entstatus: [1, 3]` 过滤（**在业 + 存续**，line 104-108；代码无注释，编码含义需抓包验证） |
| 2 | 英文名提取 | `BaseInfo.GSInfo.entNameEng`（line 207） |
| 3 | 公司富集 4 路并发 | BaseInfo / Development / bizCard / contacts（line 199-204） |
| 4 | 凭证管理 | `secret`（Token）+ `account_no`（distinct_id），active 凭证挑选（line 39-47） |
| 5 | 401/403 错误 | 抛 `CREDENTIAL_EXPIRED`（line 112-117） |
| 6 | 429 限流退避 | 指数退避重试 3 次（line 317-334） |
| 7 | 单公司失败容错 | enrich 失败仍返回 basic 记录（line 151-156） |
| 8 | 增量回调 | `on_partial` + `on_company_enriched`（line 130-132 / 173-185） |
| 9 | 并发控制 | `_DETAIL_CONCURRENCY=3` 信号量（line 14, 135） |
| 10 | 联系人配额保护 | 0.5s 前置延迟（line 15, 292） |

---

## 3. 缺口清单（Stage 1 不满足项）

### P1 — 必须改（阻塞 Phase 1 编码）

| # | 问题 | 现状 | 修改方向（**业务确认后**） |
|---|---|---|---|
| **P1-1** | 英文名缺失时 fallback 到中文名 | `name_en = name_en or company_name`（line 222-223） | **保持英文名为空原样写入**`lixiaoyun_raw_companies`（不强制 fallback 中文）；**腾道 Stage 2 在调用前判断英文名为空则自动跳过**该同行 |
| **P1-2** | 一次性跑全部分页，无配额控制 | `for page in range(1, 10_000)`（line 100） | `collect()` 增加 `max_competitors` 参数；达到上限即停止；或 Worker 在外部按 `stage1_today_count` 截断 |
| **P1-3** | 无跨天续跑能力 | 每次从 page=1 开始 | 增加 `start_page` / `skip_source_ids` 参数；Worker 把已采集 source_id 列表传入 |
| **P1-4** | 落库目标表 | 现 Worker 写 `competitor_companies` / `shared_companies` | Worker submit_result 按 `source_type=lixiaoyun` 路由到 `lixiaoyun_raw_companies`（不在 Provider 层改，Worker 改） |

### P2 — 应该改（影响数据质量/Schema 对齐）

| # | 问题 | 现状 | 修改方向 |
|---|---|---|---|
| **P2-1** | `raw_data` 结构未与新表 schema 对齐 | 嵌套 dict 塞 raw_data | 拍板 `lixiaoyun_raw_companies` 列结构（哪些抽独立列：name / english_name / source_id / domain / esdate / legalperson / uncid / employee_scale / reg_capital，剩余进 `raw_payload` JSONB） |
| **P2-2** | 联系人外溢风险 | 联系人塞 `raw_data.lx_contacts` | 明确：励销云联系人**仅归档**到 `lixiaoyun_raw_companies.raw_payload`，**不写** `shared_contacts`（那是海外买家的） |
| **P2-3** | `_extract_list` 多 fallback key 偏粗 | 6 个 key 兜底（line 353） | 抓包确认实际响应结构后精简，留 1-2 个主要 key |

### P3 — 待业务确认（不改也能跑）

| # | 问题 | 现状 | 待确认 |
|---|---|---|---|
| **P3-1** | 搜索精度 | 仅按 keyword + entstatus 过滤 | 搜 "PCB" 会带回大量非生产型公司（贸易/咨询/空壳）。是否需要加产业/规模筛选？反正不进 clean，影响有限，可先不做 |
| **P3-2** | 联系人是否每家都拉 | 是，每家 0.5s 延迟 + 消耗配额 | Stage 1 核心是英文名，联系人是次要；可改为「英文名空时不拉联系人」或「全跳过联系人」 |
| **P3-3** | 凭证字段验证 | 现仅 `secret` + `account_no`；其他 header (`app_token`, `crm_platform_type`, `platform_type`, `brand`, `project_name`) 全部硬编码 | **结论**：维持 2 个凭证字段；`app_token`(32 位 MD5 风格 AppKey) 看似跨账号一致但**无第二账号抓包对比无法 100% 验证**；`raw_config` JSONB 兜底位保留，发现 app_token 多变时不改 schema 直接 overlay |

### P4 — 不改但需对齐

| # | 内容 |
|---|---|
| **P4-1** | 401 → `AppError(status_code=503)` 与 spec §2.6「凭证失效自动停源」逻辑契合 ✅ |
| **P4-2** | 429 内置退避 vs 全局 `AsyncTokenBucket`（spec §3.5）的关系：建议保留 Provider 内置退避作 last-mile 防护，全局 token bucket 在 Worker 层做整体节流 |

---

## 4. 风险点

| 风险 | 影响 | 缓解 |
|---|---|---|
| 励销云内部 API 结构调整 | `GSInfo.gsInfo.entNameEng` 路径深，一旦改名英文名直接拿不到 | 落 `raw_payload` JSONB 全量保留，路径变更时回查 |
| 凭证生命周期 | Token 过期间隔未知 | 401 自动停源 + 站内通知运营，依赖现有机制 |
| 关键词召回噪声 | 搜 "PCB" 含大量非生产型公司 | 励销云不进 clean，仅做腾道 Stage 2 输入；英文名为空时跳过，自然过滤掉一批空壳 |
| 联系人配额消耗 | 每家 0.5s 前置 + 真实配额 | Stage 1 不必拉联系人（次要数据，可关闭 contacts 调用减少配额消耗） |

---

## 5. R-3 结论

**励销云 Provider 主体可用**：核心搜索 + 富集 + 错误处理 + 凭证机制已就绪。

**Phase 1 编码前必做的 4 个 P1 改动（业务已确认 2026-04-30）**：

1. **英文名为空原样写入**（不 fallback 中文名）；腾道 Stage 2 在调用前判断英文名为空则自动跳过 — **Provider 层 + Tendata Provider 双向小改**
2. 配额上限参数 `max_competitors` — **Provider 层小改 + Worker 接入**
3. 跨天续跑参数 `skip_source_ids` 或 `start_page` — **Provider 层小改 + Worker 接入**
4. Worker 写库路由按 source_type 分发到 `lixiaoyun_raw_companies` — **Worker 改**

**P3 业务决策（2026-04-30 已确认）**：
- P3-1 搜索精度过滤：用户更正 `entstatus: [1, 3]` 实际语义为「在业 + 存续」（编码含义需抓包二次验证）；不增加产业/规模过滤，让腾道 Stage 2 自然过滤
- P3-2 联系人接口：**保持现状每家都拉**（即使只 Admin 后台用，业务希望保留）
- P3-3 凭证字段：**仅录入 `secret` + `account_no` 两字段**；其余 header 当作硬编码常量；`app_token` 待第二账号抓包验证

**总体改造工作量**：~半天 Provider + 0.5-1 天 Worker schema 适配

**不需要重写**，原始实现质量良好，关键路径都覆盖到了。

---

## 6. 与 Phase 1 对接的具体接口契约（建议）

```python
# 新接口签名（建议）
class LixiaoyunCollectionProvider(CollectionProvider):
    async def collect(
        self,
        task: CollectionTask,
        max_competitors: int = 30,           # 新增：本次最多采集 N 家（Stage 1 日配额）
        skip_source_ids: set[str] = None,    # 新增：已采集过的 source_id（跨天续跑用）
        skip_contacts: bool = False,         # 新增：是否跳过联系人调用（节省配额）
    ) -> CollectionPayload:
        ...

# CollectionPayload.competitors 每条记录建议字段
{
    "source_id": str,           # 励销云内部 ID
    "company_name": str,        # 中文名
    "company_name_en": str,     # 英文名（空时跳过 → 不喂腾道）
    "domain": str | None,
    "esdate": str | None,
    "legalperson": str | None,
    "uncid": str | None,        # 统一信用代码
    "reg_capital": str | None,
    "employee_scale": str | None,
    "reg_address": str | None,
    "raw_payload": dict,        # 完整原始返回（lx_contacts 也归档于此）
    "source_type": "lixiaoyun",
}
```

Worker 端按 `source_type` 路由到 `lixiaoyun_raw_companies` 表写入；不写 `shared_contacts`、不参与 clean 管道。
