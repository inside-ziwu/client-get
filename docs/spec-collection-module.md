# 采集模块 Spec — 外贸通直采 + 反推采集

**版本**: v1.4
**日期**: 2026-04-30
**状态**: 经 plan-eng-review 工程视角审查并补丁；腾道反向工程已完成（R-1 ✅）；R-3 励销云审查已完成；Phase 1 = 外贸通直采 + 腾道反推 + 清洗（PG Outbox 异步管道）

---

## 1. Problem Statement

`blueprint` 主系统中，采集服务框架（`CollectionWorker`、`CollectionService`、`Internal API`）已搭好，但**实际能跑通的路径只有 Lixiaoyun→自动级联→Tendata 一条**，且这条链路在多个层面与真实业务需求不吻合。具体短板：

1. **外贸通完全不可用**：`WaiMaoTongCollectionProvider.collect()` 是 501 占位符，任何带 `waimao_tong` 的任务立即失败
2. **腾道实现路线错误**：当前 `tendata.py` 用 `open-api.tendata.cn` + Bearer Token 的实现假设腾道有开放 API，**实际不可用**，必须废弃；腾道与外贸通同形态——仅支持 HTTP 爬取
3. **触发模型与业务不匹配**：当前 `CollectionSchedulerService` 是「定时按 active 关键词建任务」，但业务真实模型是**关键词级订阅**——运营对一个关键词点一次「启动」，系统每天自动推进，无需人工再点
4. **缺乏日配额与跨天恢复**：单关键词外贸通直采的完整路径需要数小时（1000 公司 × 富集 ÷ 15 RPM ≈ 200 分钟），当前没有日配额机制，长任务会爆 task lease 或被外部 API 限流卡死
5. **缺凭证管理通道**：没有 Internal API 让 Worker 拉取凭证，没有 Admin 凭证录入流程
6. **采集层越界**：当前 `submit_result()` 直接写 `tenant_companies.is_precise_customer` 和 `source_marker` 等业务标记字段，与「采集 vs 清洗分层」原则冲突
7. **缺乏写竞争防护**：长 lease + 多 worker 模型下，lease 失效后旧 worker 仍可能写数据，当前只有 heartbeat 校验 lease_id

---

## 2. Proposed Solution

### 2.1 分层原则（核心架构约定）

> 🔑 **「采集是采集，清洗是清洗」**

| 层 | 职责 | 写入表 |
|---|---|---|
| **采集层** | 外部数据源 → 渠道专表 | `waimaotong_raw_companies` / `tendata_raw_companies` / `lixiaoyun_raw_companies` / `shared_contacts` / `collection_task_keywords` / `collection_keywords`（进度字段） |
| **清洗层** | 渠道专表 → 干净主表 + 租户视图 | `clean_companies`（全局 master，去重后 1 行=1 海外买家）+ `tenant_companies`（per-tenant 视图，含关键词命中 / `is_precise_customer` / `source_marker` / `business_status`） |

采集层**只写各自渠道专表**：每个 Provider 写各自原始 schema，不跨表合并、不做实体匹配。清洗层基于 3 张渠道专表 + `collection_task_keywords` 推导出 `clean_companies`（仅外贸通+腾道，励销云不进入清洗）+ `tenant_companies`。本 Spec 主要规范采集层；清洗层接口契约同步在 Phase 1 内交付。

### 2.2 采集类型（2 种独立的并行链路）

**类型 A：外贸通直采**

```
关键词 → 外贸通 SEARCH (分页公司列表)
       → 外贸通 DETAIL (每家公司详情)
       → 外贸通 CONTACT (每家公司联系人邮箱)
       → 写入 waimaotong_raw_companies (渠道专表)
       → 清洗 → clean_companies + tenant_companies (按租户关键词命中)
```

**类型 B：反推采集（2 阶段）**

```
Stage 1: 关键词 → 励销云 search → 中国 PCB 同行公司
                → 写入 lixiaoyun_raw_companies (渠道专表，仅运营可见，不进入清洗)

Stage 2: 同行英文名
            ├─ 腾道 (HTTP 爬取，已完成反向工程 ✅) → 海外买家  [Phase 1]
            └─ 外贸通反推 (HTTP 爬取，待反向工程)   → 海外买家  [Phase 2]
                → 写入 tendata_raw_companies / waimaotong_raw_companies (渠道专表)
                → 清洗 → clean_companies + tenant_companies
```

> **关键约束**：腾道**没有开放 API**，只能走 HTTP 爬取（Cookie/会话级鉴权，与外贸通同形态）。当前 `tendata.py` 实现错误，必须废弃重写。详细 API 链路与字段映射见 `docs/spec-tendata-provider.md`。
>
> 「反推-外贸通」仍需反向工程，放 Phase 2，详见第 8 节实施分期。

两种类型在系统中是并行链路，互不干扰、独立配额。

### 2.3 触发模型：关键词级订阅 + 自动推进

> **核心决策（修订 v1.2）**：放弃「轮次」概念，改为「per-keyword 订阅」。

- **订阅粒度**：以 `(keyword)` 为单位（不区分采集类型），运营在 Admin 后台关键词列表上对**每个关键词单独点「启动采集」**
- **启动一次、自动持续**：关键词从 `not_started → running` 后，每天定时调度器自动推进当日工作量；运营**不需要每天点击**
- **多类型并行**：关键词一旦启动，**两种采集类型同时跑**：Phase 1 启用「外贸通直采 + 腾道反推（Lixiaoyun Stage1 + 腾道 Stage2）」；外贸通反推 Phase 2 上线后自动接管 Stage 2 的外贸通分支。每种类型有独立的进度字段、独立的日配额
- **运营可控**：运营可以对任一 running 关键词「停止」（→ `paused`）或「重置」（→ `pending`），可以在采集中「暂停全局调度」
- **状态机**：

```
not_started ──[运营点启动]──▶ pending ──[调度器拉]──▶ running
                                                        │
                                                        ├──[当日配额满]──▶ paused（次日自动恢复）
                                                        ├──[全部跑完]──▶ done
                                                        ├──[凭证失效]──▶ paused（凭证修好自动恢复）
                                                        ├──[3 次重试失败]──▶ error（运营手动决策）
                                                        └──[运营操作]──▶ paused / cancelled

done ──[运营手动重置]──▶ pending
error ──[运营手动重试]──▶ pending
```

### 2.4 关键词模型

- **租户维度**：租户在自己的 tenant 平台维护关键词（`collection_keywords` 表，per-tenant 一行）
- **关键词中立**：关键词只有名字 + status，**不带** source_types、**不带** 国家字段（默认全球）
- **多租户共享**：当 A、B 两租户配置同关键词「PCB」，运营对该关键词启动后**只跑一次**外部 API；结果通过 `collection_task_keywords` 中间表同时关联两租户
- **软删除规则**：
  - 单租户删除关键词 → 删除该租户那一行 `collection_keywords` + 删除该租户在 `collection_task_keywords` 中的关联记录
  - 在跑任务的 `collection_task_keywords` 中**仍有其他租户关联** → 任务继续跑
  - 该关键词关联的**所有租户都删除时** → 任务标 `cancelled`，关键词在物理层最终清理（保留进度数据用于审计）
- **跑中删除**：worker 心跳时检查关联租户列表，发现全部删除则提前退出当前 task

### 2.5 日配额与跨天恢复

| 类型 | 阶段 | 日配额（默认） | 配额计量 | 进度字段 |
|---|---|---|---|---|
| 外贸通直采 | — | **10 页 / 关键词 / 天**（≈1000 公司） | 页数 | `current_page` / `total_pages` / `today_pages` / `last_run_date` / `subscription_status` |
| 反推（Phase 1，腾道） | Stage 1 | **30 同行 / 关键词 / 天**（可配置） | 同行数 | `stage1_today_count` / `stage1_total_count` / `last_stage1_date` / `stage1_status` |
| 反推（Phase 1，腾道） | Stage 2 | **100 买家 / 关键词 / 天**（可配置） | 买家数 | `stage2_today_count` / `stage2_total_count` / `last_stage2_date` / `stage2_status` |

**跨天恢复机制**：每次定时调度器运行时检查每个 running 关键词的 `last_run_date`，若 != today，重置当日计数器；继续从 `current_page` / 未反查的同行索引续跑。

**Stage1 + Stage2 联动**（Phase 1 起生效，仅腾道链路）：调度器对 running 关键词同时推进 Stage1（励销云搜未足额关键词的同行）+ Stage2（腾道反查未足额同行的买家），各自受日配额管控，互不阻塞。Phase 2 上线外贸通反推后，Stage 2 同时跑腾道+外贸通双路。

### 2.6 凭证管理

- **集中托管**：所有数据源凭证由平台运营统一录入，**Phase 1 不做租户自带凭证**（Non-goal 2）
- **Phase 1 三套凭证全部启用**：外贸通直采 + 腾道反推 + 励销云 Stage1 三条链路在 Phase 1 全部上线，对应凭证均需录入
- **Admin 录入页**：每个数据源一套凭证（外贸通 Cookie+签名密钥+device_id、励销云 Token+account_no、腾道 `token` UUID + `userId` + `JSESSIONID`）
- **加密存储**：`data_source_credentials.secret` 使用应用层加密
- **Internal API 下发**：`GET /internal/api/v1/collection/credentials/{source_type}` 给采集 Worker 拉取明文凭证（服务间认证 + scope=`collection:read`）
- **失效自动停源**：HTTP 401 → 该数据源所有 active 任务暂停 + 站内通知运营管理员；运营更新凭证后下次定时调度自动恢复

### 2.7 数据归属与可见性

**三层数据架构**：

```
Layer 1: 渠道专表（采集层直接落库，每个数据源一张原始表，保留原始 schema）
   ├─ waimaotong_raw_companies   (外贸通直采 + 外贸通反推 Phase 2)
   ├─ tendata_raw_companies      (腾道反推)
   └─ lixiaoyun_raw_companies    (励销云 Stage1，中国同行)

Layer 2: 干净公司表（清洗层产物，全局 master）
   └─ clean_companies            (从 waimaotong_raw + tendata_raw 去重清洗合并；不含励销云)

Layer 3: 租户视图（清洗层按关键词命中规则生成）
   └─ tenant_companies           (per-tenant 行：tenant_id, clean_company_id, matched_keyword,
                                  is_precise, status, 各操作时间戳)
```

**归属与可见性表**：

| 数据 | 归属表 | 写入层 | Tenant 可见 | Admin 可见 |
|---|---|---|---|---|
| 外贸通采集原始数据 | `waimaotong_raw_companies` | 采集 | ❌（不直接） | ✅ |
| 腾道采集原始数据 | `tendata_raw_companies` | 采集 | ❌（不直接） | ✅ |
| 励销云采集原始数据（中国同行） | `lixiaoyun_raw_companies` | 采集 | ❌ **永不展示** | ✅ |
| 联系人原始数据 | `shared_contacts` | 采集 | ❌（不直接） | ✅ |
| 任务-租户-关键词归属链路 | `collection_task_keywords` | 采集 | — | — |
| **干净公司主数据**（去重清洗后） | `clean_companies` | **清洗** | ✅（仅经 tenant_companies） | ✅（master 视图） |
| **租户视图**（关键词命中 + 状态追踪） | `tenant_companies` | **清洗** | ✅ | ✅ |

> 🔑 关键架构原则：
> 1. **采集层只写渠道专表**，不跨表合并、不做去重。每个 Provider 写各自的 raw 表，schema 保留各自原始字段。
> 2. **励销云专表不进入清洗管道**（中国同行 ≠ 海外买家），仅作为腾道反推的输入源 + Admin 数据归档。
> 3. **清洗层产出 `clean_companies`（全局 master）+ `tenant_companies`（租户视图）**：租户侧根据自己配置的关键词从 `tenant_companies` 视图查询，不复制公司行到每个租户。
> 4. **Admin 后台展示 3 张渠道专表 + clean_companies**，便于运营审查原始采集数据与清洗结果。

#### 2.7.1 清洗触发契约（PG Outbox 模式）

> 与 §3.5「不引入消息队列」约束兼容，使用 PostgreSQL 自身实现 Outbox 异步管道。

**核心机制**：
- 新增 `cleanup_queue` 表（PG Outbox），存放待清洗的 raw 行引用
- Worker `submit_result` 在**单事务内**完成「写 raw 表 + 入队 cleanup_queue」，保证 raw 落库与清洗触发的原子性
- 清洗服务循环消费 `cleanup_queue`，用 `FOR UPDATE SKIP LOCKED` 支持多实例并发
- 失败重试：`status='failed'` + `attempts++`；attempts<3 定时 reset 回 `pending`；attempts>=3 通知运营

**Worker submit_result 事务**：
```sql
BEGIN;
  INSERT INTO {tendata|waimaotong|lixiaoyun}_raw_companies (...) RETURNING id;
  INSERT INTO cleanup_queue (raw_table, raw_row_id, task_id)
    VALUES ('xxx_raw_companies', :id, :task_id)
    ON CONFLICT (raw_table, raw_row_id) DO NOTHING;
COMMIT;
```
> 注意：励销云 raw 行也入队，但清洗服务**判断 raw_table=lixiaoyun_raw_companies 直接标 done**（不进 clean）—— 入队是为了对账（"raw 已入队 vs 已处理"统计）。

**清洗服务消费循环**（建议每 1-2 秒拉一次，单批 100）：
```sql
BEGIN;
  SELECT id, raw_table, raw_row_id FROM cleanup_queue
   WHERE status = 'pending'
   ORDER BY id LIMIT 100
   FOR UPDATE SKIP LOCKED;
  -- 处理：UPSERT clean_companies + UPSERT tenant_companies + array_append matched_keywords
  UPDATE cleanup_queue SET status = 'done', processed_at = NOW() WHERE id IN (...);
COMMIT;
```

**幂等键**：`(raw_table, raw_row_id)` UNIQUE，重复入队 NO-OP；清洗逻辑用 UPSERT 保证多次重放结果一致。

**批量重算**：清洗算法升级时手动 `UPDATE cleanup_queue SET status='pending' WHERE ...` 重置即可。

### 2.8 失败处理

| 错误类型 | 检测精确路径 | 行为 |
|---|---|---|
| RPM 限流 | 外贸通：HTTP 429 / response `code="429"`；腾道：HTTP 429 / response `code=429`；励销云：HTTP 429 + `Retry-After` 头 | 关键词标 `paused`，下次定时调度恢复 |
| 凭证失效 | 外贸通：HTTP 401 + 响应体 `success=false`；腾道：HTTP 401 / response `code=401`；励销云：HTTP 401/403（实际抓包确认） | Provider 抛 `CredentialExpiredError` → Worker 把该数据源所有 active 任务标 `paused` + `notifications` 表写一条给运营 |
| 单关键词其他 API 错误 | HTTP 5xx 重试 3 次（3s/9s/27s）后仍失败 / 422 / 解析错误 | 标 `error` + `error_msg`，运营手动决策重试或跳过 |
| 单公司 DETAIL/CONTACT 失败 | 单次调用失败 | 跳过该公司富集，保留 search 结果，不影响其他公司 |
| 网络超时 / 5xx | 偶发 | 指数退避重试 3 次 |
| 全部租户删了该关键词 | worker 心跳时检查 | 提前 `cancelled` 退出 task |
| 清洗失败 | cleanup_queue.status='failed' & attempts>=3 | 通知运营人工介入，raw 行已落库不丢失 |

> 实施约定：每个 Provider 自行封装渠道特异的失效检测信号，统一转为 `CredentialExpiredError` 异常向 Worker 抛出，便于通用错误分类逻辑。

### 2.9 进度可视化（Admin 端）

**采集主页 = 关键词列表 + 顶部汇总面板**

- **顶部汇总面板**：今日新增公司数 / 今日新增联系人数 / 今日推进的 running 关键词数 / 当前 paused / 当前 error
- **关键词列表（每行）**：keyword / 各类型 status / today/total 进度 / 累计公司数 / 累计联系人数 / last_run_date / error_msg
- **运营操作**：每行支持「启动采集」（`not_started→pending`）/「停止」（`*→paused`）/「重置」（`done→pending`）/「重试」（`error→pending`）

不做事件流（不需要分钟级 push），按关键词字段更新时间渲染。

---

## 3. Technical Constraints

### 3.1 API 限流（外部）

| 数据源 | 接口形态 | RPM/账号 | 页间延迟 | 备注 |
|---|---|---|---|---|
| 外贸通 | HTTP 爬取（Cookie+签名） | 15 | 3-8 秒随机 | 原始 repo `flows/utils/netease_api.py` 可参考 |
| 励销云 | HTTP 爬取（Token+headers） | 沿用现有 `lixiaoyun.py` | — | `_DETAIL_CONCURRENCY=3` |
| 腾道 | HTTP 爬取（Cookie/会话） | 与外贸通相近，3-5 秒随机延迟 | ~3-5 秒 | 鉴权：`token` UUID + `userId` + `JSESSIONID`（无签名）；7 个接口已抓包确认，见 8.2 R-1 |

### 3.2 数据源接入形态（统一）

三个数据源**全部走 HTTP 爬取**：
- 全部通过反向工程获取接口 URL/Header/Body 格式
- 全部通过 Cookie/Token + 签名/headers 鉴权
- 全部由平台运营手动维护凭证，失效时手动更新
- 全部使用 `httpx.AsyncClient` 异步调用

### 3.3 写竞争守护（核心安全约束）

> 🔴 **所有写入操作必须 `lease_id` 守护**

- `heartbeat` / `submit_result` / `mark_failed` / 关键词进度字段更新（`current_page` / `today_pages` 等）/ `shared_*` 写入 — 全部加 `WHERE lease_id = :lease_id` 校验
- Worker 内部维护 `cancellation_token`：心跳失败时立即置位，写入路径检查到 token 后**主动停止**所有写动作
- 这避免「lease 失效 → recover_expired_tasks 回收 → 新 worker 接手 → 旧 worker 网络恢复后继续写」的并发污染

### 3.4 长时任务保障

- 单个外贸通直采轮次单关键词最长 ~200 分钟
- task `lease_seconds`: 300（5 分钟）；心跳间隔: 30 秒
- 心跳失败 5 分钟后由 `recover_expired_tasks` 回收
- 关键词进度字段（`current_page`、`today_pages`、`stage1_*`、`stage2_*`）实时持久化到 `collection_keywords` 表（不是 `collection_tasks` 表），保证 task 重新 claim 后续跑正确

### 3.5 技术栈对齐

- 异步：`httpx.AsyncClient` 替代原始 repo 的同步 `requests`
- 限流：自实现 `AsyncTokenBucket`（asyncio.Lock + deque）
- 不引入：Playwright/浏览器自动化、消息队列

### 3.6 数据库 Schema 影响（详细字段见 §8.1）

**新增表（Phase 1，6 张）**：

| 表 | 用途 | 关键约束 |
|---|---|---|
| `waimaotong_raw_companies` | 外贸通采集原始数据 | `(source_id)` UNIQUE；`collection_type ENUM('direct_search','reverse_lookup')` 字段区分直采/反推（Phase 2 反推共用此表）|
| `tendata_raw_companies` | 腾道采集原始数据 | `tid` PRIMARY KEY；BRIEF 失败的 T1 搜索结果**不入库**（避免脏数据）|
| `lixiaoyun_raw_companies` | 励销云中国同行 | `(source_id)` UNIQUE；**无 tenant_id**，保留 `task_id` FK，租户归属通过 `collection_task_keywords` 反查 |
| `clean_companies` | 全局干净公司主数据 | `UNIQUE(name_normalized, country_iso3)`；`UNIQUE(domain) WHERE domain IS NOT NULL`；强制 `INSERT ... ON CONFLICT DO UPDATE` UPSERT |
| `tenant_companies` | 租户视图 | `UNIQUE(tenant_id, clean_company_id)`；`matched_keywords TEXT[] DEFAULT '{}'`（数组列，命中多关键词用 array_append）；GIN 索引支持包含查询 |
| `cleanup_queue` | PG Outbox 异步清洗队列 | `UNIQUE(raw_table, raw_row_id)` 幂等键；`status ENUM('pending','processing','done','failed')`；`(status='pending')` 部分索引 |

**name 标准化算法**（`normalize_company_name(text) RETURNS text`）：
```
1. UPPER → 转大写
2. 去标点：替换 [.,;:'"()&\-] → 空格
3. 去尾部公司形式词（白名单）：SDN BHD / PVT LTD / PRIVATE LIMITED / CO LTD / CO. / INC / CORP / LLC / GMBH / MFG / 等
4. 去首尾空白 + 压缩多空格为单空格
示例：
  "Filtermation Mfg. Sdn Bhd"           → "FILTERMATION"
  "POSIFLOW RETAIL PRIVATE LIMITED"     → "POSIFLOW RETAIL"
  "Finest PCB Shenzhen Co.,Ltd"          → "FINEST PCB SHENZHEN"
```

**country 编码统一规则**：所有表统一存 **ISO 3166-1 alpha-3**（如 `MYS`、`IND`、`CHN`）：
- 腾道 BRIEF 原生返回 ISO3 → 直接存
- 外贸通可能返国名/ISO2 → 采集层落库前转换
- 励销云返中国 → 固定 `CHN`

**字段调整**：
- `collection_keywords`：
  - 移除 `source_types` / `countries` 字段（中立化）
  - 增加状态机 `subscription_status`、各路进度字段（直采 `current_page` / 反推 `stage1_*` / `stage2_*`）、`daily_*_limit` 配额
- `data_source_credentials`：增加 `raw_config` JSONB 字段，承载三套凭证差异（外贸通签名密钥/device_id、腾道 token/userId/JSESSIONID、励销云 secret/account_no）

**废弃（big-bang，dev 期无生产数据，不迁移）**：
- `shared_companies`、`company_sources`、`competitor_companies` — drop migration，原代码路径全部迁到新模型

**base.py 接口契约调整**：
```python
# CollectionTask 增加 params 自由参数槽，移除 countries
@dataclass(slots=True)
class CollectionTask:
    id: str
    keyword: str
    source_types: list[str]
    task_type: str = "competitor_search"
    competitor_names: list[str] = field(default_factory=list)
    params: dict | None = None  # 新增：max_competitors / skip_source_ids / skip_contacts 等
    on_partial: Any = None
    on_company_enriched: Any = None
    # ❌ 移除 countries 字段（spec §6.1-Q16 已中立化）

# CollectionPayload 保留三 list；每条 dict 约定 target_table 字段告诉 Worker 路由
# {"target_table": "tendata_raw_companies", "tid": "...", ...}
```

**新增异常**：
- `CredentialExpiredError`（base.py）— Provider 自行封装渠道特异 401 信号，统一向 Worker 抛出

**新增 API**：
- 凭证 Internal API endpoint（`GET /internal/api/v1/collection/credentials/{source_type}`）
- 清洗服务消费 `cleanup_queue` 的内部 worker（轮询 1-2 秒，单批 100，FOR UPDATE SKIP LOCKED）

**时区约定**：`last_run_date` / `last_stage1_date` / `last_stage2_date` 等日期字段以 **Asia/Shanghai** 为准，跨天恢复重置走原子 SQL `UPDATE ... WHERE last_run_date < CURRENT_DATE AT TIME ZONE 'Asia/Shanghai'`

**不预留**：`tenant_id` 扩展位（未来若做租户级凭证再 migration）

---

## 4. Non-goals（明确不做的事）

1. **凭证自动刷新（Playwright 浏览器化）** — 凭证失效手动更新，不引入浏览器自动化
2. **租户自带凭证** — Phase 1 全部走平台统一凭证，schema 也不预留扩展位
3. **关键词类型标签** — 关键词中立，不绑定 source_types
4. **关键词国家字段** — 不做国家粒度，所有采集默认全球
5. **「反推-外贸通」实施** — Phase 2 才做（外贸通反推接口待反向工程；「反推-腾道」Phase 1 已上线）
6. **采集轮次实体** — 不建 `collection_runs` 表，订阅模型替代轮次
7. **同行公司给租户看** — 仅运营可见，励销云专表永不展示给租户
8. **分钟级实时进度推送** — 进度页按字段更新时间渲染，无 SSE/WebSocket
9. **BASEINFO（外贸通采购商 ID 补全）接口** — 与「反推-外贸通」一并放 Phase 2
10. **多账号轮换** — 单账号先跑，未来按需扩展 `AccountRotator`
11. **跨数据源公司去重的高级匹配（trigram、向量）** — Phase 1 清洗用 `(name 标准化 + country)` + `domain` 双键去重，不做模糊匹配；高级实体匹配后续迭代
12. **采集层判定 `is_precise_customer` / `source_marker` / `business_status`** — 这些字段是清洗层产物，不归采集层
13. **采集层写 `clean_companies` / `tenant_companies`** — 采集层只写渠道专表（`waimaotong_raw_companies` / `tendata_raw_companies` / `lixiaoyun_raw_companies`），干净表与租户视图由清洗层负责
14. **关键词自动周期重采** — 不做时间触发的自动重采，但运营可手动重置 done 关键词

---

## 5. Success Criteria

### 5.1 功能验收

1. ✅ 平台运营在 Admin「数据源配置」页可录入/更新外贸通、励销云、腾道三套凭证（Phase 1 起三套全启用）
2. ✅ 平台运营在 Admin「采集启动」页对每个关键词点击「启动采集」/「停止」/「重置」/「重试」
3. ✅ 关键词启动后无需人工再操作，每天定时调度器自动推进
4. ✅ 外贸通直采：每关键词跑到当日 10 页暂停；第 2 天接着上次的页数跑；总页数跑完标 `done`，结果落 `waimaotong_raw_companies`
5. ✅ 腾道反推（Phase 1）：Stage1（励销云搜同行）/ Stage2（腾道反查买家）各自跨天恢复，独立配额；结果落 `lixiaoyun_raw_companies` / `tendata_raw_companies`
6. ✅ 清洗管道：`waimaotong_raw_companies` + `tendata_raw_companies` → `clean_companies`（去重）→ 按租户关键词命中生成 `tenant_companies` 行
7. ✅ Admin 后台展示 3 张渠道专表 + `clean_companies`（运营审查视图）
8. ✅ 租户侧根据自己的关键词配置，从 `tenant_companies` 视图查询展示干净公司数据
9. ✅ 多租户共享同关键词：跑一次外部 API，结果通过 `collection_task_keywords` 同时关联两租户；清洗层为各租户分别生成 `tenant_companies` 行
10. ✅ Admin 采集页：关键词级别进度可见 + 顶部汇总面板
11. ✅ 凭证失效：运营收到站内通知；该数据源 active 任务暂停；更新凭证后下次定时调度自动恢复
12. ✅ 限流：单关键词自动 `paused`，下次定时调度恢复
13. ✅ 关键词软删除：所有关联租户都删除时，task 标 `cancelled` 提前退出
14. ✅ 长 lease 写竞争防护：lease 失效后旧 worker 不能再写
15. ✅ PG Outbox 管道：raw 落库 + cleanup_queue 入队同事务原子；清洗服务多实例并发消费（FOR UPDATE SKIP LOCKED）；失败重试 3 次后通知运营
16. ✅ 时区一致性：跨天恢复以 Asia/Shanghai 为准，UTC 服务器部署不出现"提前重置"或"卡住不恢复"
17. ✅ Admin 清洗管道健康页：4 个指标面板（pending 数 / 最早 pending 时长 / failed 累积 / 吞吐速率）+ 3 个对账差集列表（详见 §5.4）

### 5.2 测试验收（分层）

**Mock 层（自动化 CI 必跑）**：
1. 单测：外贸通 MD5 签名、`AsyncTokenBucket`、payload 字段映射、错误分类（限流/凭证/其他）
2. 单测：状态机转换（pending → running → paused → done 等）、关键词软删除、写入操作 lease_id 守护
3. 集成测试（mock HTTP）：管理员启动 → tasks 创建 → worker claim/heartbeat/submit → 数据落库 → 状态推进
4. 集成测试（mock 时间）：跨天恢复（第 1 天跑到上限 paused → 调时间到第 2 天 → 调度推进继续跑）
5. 集成测试：写竞争 — 模拟 lease 失效后旧 worker 写入被拒绝

**烟雾测层（手动，部署前）**：
1. 用真实凭证跑一个真实关键词（小集合，10 页）
2. 凭证失效演练：禁用一次 Cookie，确认任务进入 `paused` + 通知到位
3. 跨天恢复实跑：等待 2 天周期完整观察行为

### 5.3 数据正确性

1. ✅ 同关键词多次跑 + 重置后再跑，3 张渠道专表各自通过 `(source_id)` + 数据源原生唯一键去重，不重复
2. ✅ `clean_companies` 通过 `(name 标准化 + country)` + `domain` 去重，外贸通+腾道两源同一公司合并为单行
3. ✅ `tenant_companies` 通过 `(tenant_id, clean_company_id)` 唯一约束，不为同一租户重复生成视图行
4. ✅ `shared_contacts` 通过 `(clean_company_id, email)` 去重
5. ✅ `lixiaoyun_raw_companies` 去重键基于「同行不归租户」设计（无 tenant_id 字段或 nullable）
6. ✅ 关键词的累计公司数、累计联系人数与实际写入条数一致
7. ✅ `collection_task_keywords` 关联完整，清洗层据此推导租户归属并生成 `tenant_companies` 行
8. ✅ `name_normalized` 标准化算法对常见尾部公司形式词（SDN BHD/PVT LTD/CO LTD 等白名单）能稳定输出同值
9. ✅ 清洗幂等：同一 `(raw_table, raw_row_id)` 重复入队 NO-OP；清洗服务重放（手动重置 status=pending）后 `clean_companies` / `tenant_companies` 行不重复，仅字段更新
10. ✅ `country_iso3` 字段在 3 张 raw 表内统一为 ISO 3166-1 alpha-3 编码（外贸通若返国名/ISO2 已在采集层转换）

### 5.4 监控对账（清洗管道健康观察）

> 目的：运营能第一时间发现清洗管道堵塞 / 失败累积 / 数据丢失，且具备 SQL 级对账能力。Phase 1 末尾交付，**上线前必须有**。

#### 5.4.1 健康指标面板（Admin 后台「清洗管道健康」页）

| 指标 | 健康值 | 报警阈值 | 含义 |
|---|---|---|---|
| `cleanup_queue` 中 `status='pending'` 行数 | < 100 | > 1000 | 待清洗积压 |
| 最早 pending 行的 `enqueued_at` 距今时长 | < 5 分钟 | > 30 分钟 | 清洗滞后程度 |
| `status='failed'` & `attempts >= 3` 累积数 | 0 | > 0 立即通知 | 反复失败的死信 |
| 清洗服务每分钟处理量（`done` 增量） | > 0（有任务运行时） | 持续 5 分钟为 0 | 清洗服务存活 |

#### 5.4.2 对账差集视图（3 条 SQL，Admin 直接查）

**差集 A：raw 已落但 cleanup_queue 没入队**（事务原子性破坏，应永远为空）：
```sql
SELECT r.* FROM tendata_raw_companies r
WHERE NOT EXISTS (
  SELECT 1 FROM cleanup_queue q
  WHERE q.raw_table = 'tendata_raw_companies' AND q.raw_row_id = r.id
);
-- 同样查询应用于 waimaotong_raw_companies / lixiaoyun_raw_companies
```

**差集 B：清洗反复失败的死信列表**（运营介入决策）：
```sql
SELECT * FROM cleanup_queue
WHERE status = 'failed' AND attempts >= 3
ORDER BY enqueued_at;
```

**差集 C：task 完成但 raw 行未全部清洗**（提前结束告警）：
```sql
SELECT task_id,
       COUNT(*) FILTER (WHERE status='done') AS done_cnt,
       COUNT(*) AS total_cnt,
       COUNT(*) FILTER (WHERE status='pending') AS still_pending,
       COUNT(*) FILTER (WHERE status='failed') AS failed_cnt
FROM cleanup_queue
WHERE task_id IN (SELECT id FROM collection_tasks WHERE status='done')
GROUP BY task_id
HAVING COUNT(*) FILTER (WHERE status='done') < COUNT(*);
```

#### 5.4.3 不做（5.4 范围之外，后续迭代）

- ❌ 时序图表（pending 数趋势线等）
- ❌ Prometheus / Grafana 集成
- ❌ 自动告警（邮件/IM），仅站内 `notifications` 写入
- ❌ 历史 cleanup_queue 数据归档（7 天后可清理 done 状态行，写定时任务即可）

---

## 6. 决策回溯

### 6.1 v1.0 决策（17 项）

| # | 问题 | 决策 |
|---|---|---|
| Q0 | 腾道接入形态 | HTTP 爬取（无开放 API），与外贸通同形态，需反向工程 |
| Q1 | 触发方式 | 手动启动一次「轮次」 *(v1.2 修订)* |
| Q2 | 轮次驱动维度 | 选采集类型 + 选关键词集合 *(v1.2 修订)* |
| Q3 | 采集类型粒度 | 2 种（直采 + 反推），反推内部并行多路 |
| Q4 | 反推-外贸通接口 | 待反向工程（Phase 2） |
| Q5 | 关键词是否带类型标签 | 不带，关键词中立 |
| Q6 | 多租户共享数据分配 | 跑一次，结果共享 |
| Q7 | 外贸通直采采集深度 | 跨天恢复，每天上限直到全部完成 |
| Q8 | 反推进度模型 | 2 阶段独立，每阶段日配额 |
| Q9 | 反推启动行为 | Stage1 + Stage2 一起推进 |
| Q10 | 凭证管理 | 平台运营集中录入 |
| Q11 | 同行公司归属 | 落库 + 仅运营可见，不展示给租户 |
| Q12 | 轮次实体 | 虚拟概念，不入业务表 |
| Q13 | 重新采集 | 本期不支持 *(v1.2 修订)* |
| Q14 | 进度可见性 | 关键词级别 + 汇总面板 |
| Q15 | 失败处理 | 限流 paused / 凭证失效停源 / 其他 error |
| Q16 | 关键词国家字段 | 不填，默认全球 |
| Q17 | 日配额具体值 | 直采 10 页 / 反推 30 同行 / 反推 100 买家（可配置） |

### 6.2 v1.2 修订（10 项）

| # | 修订 | 决策 |
|---|---|---|
| R1 | 触发模型 | 改为 **per-keyword 订阅 + 自动推进**：点一次启动，每天自动跑（覆盖 Q1） |
| R2 | 订阅粒度 | **仅 keyword 级开关，两类型同时跑**（覆盖 Q2） |
| R3 | Phase 1 范围 | 已确认腾道 API 不可用，**保持 Phase 1 = 外贸通直采** *(v1.3 修订：腾道反向工程已完成，Phase 1 扩展为「外贸通直采 + 腾道反推 + 清洗」)* |
| R4 | 重新采集 | **运营可手动重置 done 关键词**（覆盖 Q13 部分） |
| R5 | 写竞争 | **所有写操作 lease_id 守护** + cancellation_token |
| R6 | 关键词软删除 | **所有关联租户都删才整体中断 + 软删除**；个别租户删不影响 task |
| R7 | 采集 vs 清洗分层 | **Spec 明确采集边界**：is_precise_customer/source_marker/scoring 全部排除出采集 Spec |
| R8 | tenant_companies 写入 | **采集只写 shared_***；租户关联（含 tenant_companies）全交清洗层 |
| R9 | 测试分层 | **Mock 测（CI 必跑）+ 烟雾测（手动部署前）** |
| R10 | Schema 增量 | **加 Phase 1 Schema 增量表**（不到 DDL 层级），见 §8.1 |
| R11 | 同行展示 | **保持 Q11 决策**，不重评 |
| R12 | 凭证扩展位 | **不预留** tenant_id 扩展位 |

### 6.3 v1.3 修订（5 项）

| # | 修订 | 决策 |
|---|---|---|
| V1 | 腾道反向工程 | **R-1 已完成 ✅**（2026-04-30），7 接口链路 + 15 字段映射 + 联系人 3 分支去重均已确认，详见 `docs/spec-tendata-provider.md` |
| V2 | Phase 1 范围扩展 | Phase 1 = 「外贸通直采 + 腾道反推（Lixiaoyun Stage1 + 腾道 Stage2）+ 清洗」；Phase 2 仅剩「外贸通反推 + BASEINFO」 |
| V3 | 数据分层架构 | 引入「3 张渠道专表 → clean_companies → tenant_companies」三层模型，废弃 `shared_companies` / `company_sources` / `competitor_companies` 旧三表 |
| V4 | 干净表模型 | `clean_companies` 为全局 master（去重后 1 行=1 海外买家）；`tenant_companies` 为 per-tenant 视图（含关键词命中 + 状态追踪），不复制公司行 |
| V5 | 励销云专表定位 | 励销云专表仅作 Admin 数据归档 + 腾道反推输入源，**不进入 clean_companies 清洗管道**（中国同行 ≠ 海外买家）|

### 6.4 v1.4 修订（10 项，闭环 plan-eng-review 阻塞项）

| # | 修订 | 决策 |
|---|---|---|
| W1 | tenant_companies 关键词命中模型 | **不拆表**，用 `matched_keywords TEXT[]` 数组列；命中多关键词 `array_append`，删关键词 `array_remove`；GIN 索引；后期遇到性能问题再拆表 |
| W2 | base.py 接口契约改造 | **折中方案**：CollectionTask 加 `params: dict \| None`、移除 `countries`；CollectionPayload **保留三 list**，每条 dict 约定 `target_table` 字段告诉 Worker 路由 |
| W3 | 清洗触发契约 | **PG Outbox 模式**（与 §3.5 不引入 MQ 兼容）：`cleanup_queue` 表 + `FOR UPDATE SKIP LOCKED`；Worker submit_result 单事务原子写 raw + 入队；清洗服务轮询消费 1-2s/批 100；详见 §2.7.1 |
| W4 | name 标准化算法 | 定义 `normalize_company_name()`：UPPER → 去标点 → 去尾部公司形式词白名单 → 压缩空格；详见 §3.6 |
| W5 | country 编码统一 | 全表统一 ISO 3166-1 alpha-3；外贸通若返国名/ISO2 由采集层转换 |
| W6 | clean_companies 并发去重 | `UNIQUE(name_normalized, country_iso3)` + `UNIQUE(domain) WHERE NOT NULL`；强制 `INSERT ... ON CONFLICT DO UPDATE` UPSERT |
| W7 | 401 凭证失效检测路径 | base.py 引入 `CredentialExpiredError`；每个 Provider 自封装渠道特异信号；§2.8 错误表加「检测精确路径」列 |
| W8 | lixiaoyun_raw_companies 归属 | **无 tenant_id**，保留 `task_id` FK；通过 `collection_task_keywords` 反查租户 |
| W9 | 时区一致性 | 跨天恢复字段统一以 Asia/Shanghai 为准；重置走原子 `UPDATE WHERE last_*_date < CURRENT_DATE AT TIME ZONE 'Asia/Shanghai'` |
| W10 | 旧表迁移路径 | dev 期无生产数据，**big-bang drop** `shared_companies` / `company_sources` / `competitor_companies`，不做数据迁移 |

**v1.4 落地的 reviewer 其余建议**：
- ✅ 监控对账（4 健康指标 + 3 对账差集 SQL）已落到 §5.4，Phase 1 末尾交付
- ✅ waimaotong_raw_companies 加 `collection_type` 字段已落到 §3.6（兼容 Phase 2 反推）
- ✅ 腾道 BRIEF 失败时 T1 数据不入库已落到 §3.6

---

## 7. 后续待确认（不阻塞 Spec 落地）

- 凭证失效通知是否需要邮件/IM 渠道（当前仅站内 `notifications` 表）
- worker 并发数（同时跑几个关键词的 task）—— 受 RPM 全局限流自然收敛，建议先 1-2 起步
- 「反推-外贸通」R-2 反向工程的执行人与时间窗（Phase 2 启动前完成）
- 清洗层独立 Spec 文档化（v1.4 已确定 PG Outbox 触发契约、UPSERT 算法、normalize 算法；剩具体实现细节如 normalize 白名单完整列表 / domain 提取规则等可在编码时补）
- 定时调度器的运行频率（默认建议每天 02:00 跑一次；是否支持多次/天的运营配置）
- 励销云 `entstatus: [1, 3]` 编码含义二次抓包验证（用户口径："在业 + 存续"）
- 励销云 `app_token` 是否跨账号一致（待第二份真实凭证对比验证）

> v1.3 时未解决的 7 项待确认中，5 项已在 v1.4 落地（lixiaoyun_raw 归属 / 清洗触发契约 / 双键去重算法 / tenant_companies 写入触发 / 时区）。

---

## 8. 实施分期

Spec 第 2 节定义的 2 种采集类型是**最终产品形态**。腾道反向工程（R-1）已完成，Phase 1 范围扩展为「外贸通直采 + 腾道反推 + 清洗」；仅外贸通反推（R-2 待做）放 Phase 2。

### 8.1 Phase 1（即时实施）：外贸通直采 + 腾道反推 + 清洗

**前置研究任务**：
- ✅ R-1：腾道反向工程（**已完成**，详见 §8.3）
- 🔬 R-3：励销云接口审查 — 复核现有 `lixiaoyun.py` 的 search / detail / contacts 是否满足 Stage1 需求；输出补丁清单。**Phase 1 启动前必须完成**

**功能范围**：

| 模块 | 范围 |
|---|---|
| 外贸通直采 | SEARCH → DETAIL → CONTACT 完整闭环，落 `waimaotong_raw_companies` |
| 腾道反推 Stage 1 | 励销云搜索关键词 → 中国 PCB 同行公司，落 `lixiaoyun_raw_companies` |
| 腾道反推 Stage 2 | 同行英文名 → 腾道 7 接口链路 → 海外买家，落 `tendata_raw_companies`（实现见 `spec-tendata-provider.md`） |
| 凭证管理 | 三套凭证全启用（外贸通 / 腾道 / 励销云）；Admin 录入页 + 加密存储 + Internal API 下发 |
| Admin 后台 | 关键词列表 + 启动/停止/重置/重试；进度跟踪页（直采 `current_page` + 反推 `stage1_*` / `stage2_*`）；3 张渠道专表 + `clean_companies` 数据归档浏览页 |
| 调度器 | 每天定时推进所有 running 关键词；同时驱动直采 + Stage1 + Stage2 三路 |
| 限流/恢复 | 限流 paused → 次日自动恢复；凭证失效通知 + 任务暂停；错误指数退避；跨天恢复 |
| 写竞争守护 | 所有写操作 `lease_id` 校验 + cancellation_token |
| 关键词软删除 | 多租户引用计数，所有租户都删才中断 |
| 清洗管道 | `waimaotong_raw_companies` + `tendata_raw_companies` → `clean_companies` 去重；按 `collection_task_keywords` 关键词命中规则生成 `tenant_companies` 视图行 |
| 租户侧 | 租户根据自己关键词配置，从 `tenant_companies` 视图查询展示干净公司数据 |

**Phase 1 不做**：
- ❌ 外贸通反推路径（待 R-2 完成）
- ❌ BASEINFO 采购商 ID 补全
- ❌ 高级实体匹配（trigram / 向量），Phase 1 清洗用 `(name 标准化 + country)` + `domain` 双键去重
- ❌ 励销云数据进入 clean 管道（永久不做）

**Phase 1 同步处理**：
- 🔄 现有错误的 `tendata.py`（open-api 实现）按 R-1 结果**重写**为 HTTP 爬取实现
- 🔄 现有 `lixiaoyun.py` 按 R-3 审查结果**适配** Stage1 模型
- 🔄 旧的 `shared_companies` / `company_sources` / `competitor_companies` 三表 schema **废弃**（数据迁移或归档），由新「3 渠道专表 + clean + tenant」模型替代

**Phase 1 Schema 增量**：

新增表（5 张）：

| 表 | 用途 | 关键字段 |
|---|---|---|
| `waimaotong_raw_companies` | 外贸通直采原始 | source_id, name, country, domain, industry, phone, customs_data, emails[], raw_payload |
| `tendata_raw_companies` | 腾道反推原始 | tid (PK), globizId, name, country, aliases[], website, taxNo, incorporationDate, employeeNum, industryDesc, total_sumOfMoney, total_trades, contacts_count, raw_payload |
| `lixiaoyun_raw_companies` | 励销云中国同行 | source_id, name (中文), english_name, ... 字段贴合励销云 detail 返回 |
| `clean_companies` | 全局干净公司主数据（去重后） | id (PK), name_normalized, country, domain, industry, products[], contacts_count, sources[]（来自哪几张 raw 表）, last_updated |
| `tenant_companies` | 租户视图（per-tenant） | tenant_id, clean_company_id, matched_keyword, is_precise, status, created_at, last_action_at；唯一约束 `(tenant_id, clean_company_id)` |

`collection_keywords` 字段增量：

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `subscription_status` | enum | `'not_started'` | 状态机 |
| `current_page` / `total_pages` / `today_pages` | INT | 0 | 外贸通直采进度 |
| `stage1_today_count` / `stage1_total_count` / `stage1_status` / `last_stage1_date` | — | — | 励销云 Stage1 进度 |
| `stage2_today_count` / `stage2_total_count` / `stage2_status` / `last_stage2_date` | — | — | 腾道 Stage2 进度 |
| `last_run_date` | DATE | NULL | 跨天恢复判断 |
| `total_companies` / `total_contacts` | INT | 0 | 累计计数 |
| `error_msg` | TEXT | NULL | 最后一条错误 |
| `started_at` | TIMESTAMPTZ | NULL | 启动时间 |
| `daily_page_limit` / `daily_stage1_limit` / `daily_stage2_limit` | INT | 10 / 30 / 100 | 各路日配额 |
| ❌ `source_types` / `countries` | — | — | **删除**（中立化 + 全球默认） |

`data_source_credentials`：增加 `raw_config` JSONB 字段，承载三套凭证差异结构。

`collection_tasks`：所有写操作 SQL 加 `WHERE lease_id = :lease_id` 守护。

**Phase 1 验收**：Spec 第 5 节中所有标 ✅ 的功能验收（包括 5.1-1 三套凭证、5.1-4 直采、5.1-5 腾道反推、5.1-6 清洗管道、5.1-7 Admin 数据归档、5.1-8 租户视图、5.1-15 PG Outbox、5.1-16 时区）。

**Phase 1 实施顺序**（6 步，每步可独立 PR）：

| # | 步骤 | 产出 | 依赖 |
|---|---|---|---|
| 1 | **base.py 接口契约 + DB schema migration** | base.py 新接口（params/target_table/CredentialExpiredError）；6 张新表 DDL（3 raw + clean + tenant + cleanup_queue）；旧三表 drop migration；normalize_company_name() 函数 | 无 |
| 2 | **腾道 Provider 重写** | 新 `tendata.py` 实现 7 接口链路（基于 `spec-tendata-provider.md`）；单测覆盖 BRIEF→T3→VOT→STATS→T4 三分支 + 联系人去重 | 步骤 1 |
| 3 | **外贸通 Provider 实现** | 新 `waimaotong.py` 实现 SEARCH→DETAIL→CONTACT；签名密钥/device_id 凭证封装；单测 | 步骤 1 |
| 4 | **励销云 Provider 改造**（R-3 P1 4 项） | `lixiaoyun.py` 加 `max_competitors` / `skip_source_ids` 参数；英文名为空原样写入；单测 | 步骤 1 |
| 5 | **Worker 路由 + 清洗管道**（PG Outbox） | Worker submit_result 按 source_type 路由到 raw 表 + cleanup_queue 入队（同事务）；清洗服务 worker 循环消费（UPSERT clean + tenant + array_append matched_keywords）；失败重试机制 | 步骤 2-4 |
| 6 | **Admin UI**（采集进度 + 数据归档 + 清洗管道健康） | Admin 关键词列表/启动按钮；3 张 raw 表 + clean_companies 浏览页；凭证录入页（三套）；**清洗管道健康页**（4 指标面板 + 3 对账差集列表，详见 §5.4）| 步骤 5 |

> 步骤 2/3/4 可并行（不同人/不同 PR）；步骤 5 必须等三个 Provider 都到位才能集成测试。

### 8.2 Phase 2（前置：R-2 外贸通反推接口反向工程完成）

**前置研究任务**：
- 🔬 R-2: 外贸通反推接口反向工程 — 在已有外贸通会话上，确认「同行英文名 → 海外买家」用哪个接口（候选 BASEINFO / 其他），输出 URL/Header/Body/鉴权/响应/限流

**功能范围**：
- ✅ 外贸通 Provider 增加反推路径（基于 R-2 结果）
- ✅ Stage 2 双路并行：腾道 + 外贸通反推同时跑（独立配额，结果合并）
- ✅ BASEINFO 接口（采购商 ID 补全，外贸通直采路径补充）
- ✅ 清洗管道增加外贸通反推 raw 数据合并到 `clean_companies`
- ⚠️ 高级实体匹配（trigram / 向量）— 视清洗效果决定是否启动

**Phase 2 验收**：外贸通反推链路 + BASEINFO 完整闭环；Stage 2 双路结果在 `clean_companies` 正确合并。

### 8.3 R-1 腾道反向工程结果（已完成 ✅，2026-04-30）

> 本节为 R-1 研究产出的归档摘要，详细 API/字段/联系人架构见 `docs/spec-tendata-provider.md`（5 节标准结构 Spec）。

**鉴权**：纯 Cookie，无签名。需 `token`（UUID）+ `userId` + `JSESSIONID`。两个子域：
- `data.tendata.cn` — T1 搜索
- `bizr.tendata.cn` — 公司详情 / 联系人 / 贸易统计

**7 接口链路**（按调用顺序）：

| # | 名称 | 方法 | 路径 | 关键参数 | 输出 |
|---|---|---|---|---|---|
| T1 | 贸易搜索 | POST | `data.tendata.cn/search` | `keyword`=竞对英文名, `companyType=IMPORTER` | 买家列表（name+country），无 tid |
| BRIEF | 公司 BRIEF | GET | `bizr.../api/corp/v2/companies/brief/0` | `name`, `country`, `catalog=BUYER` | **tid**, globizId, aliases[], website, taxNo, linkedins |
| T3 | 公司详情 | GET | `bizr.../api/corp/v2/companies/0/{tid}` | `tid` | incorporationDate, employeeNum, industryDesc, websites[] |
| VOT | 贸易量统计 | POST | `bizr.../api/bizr/v1/user/trade/company/report/0/volume_of_trade` | `keyword`, `aliases[]`, `companyType=IMPORTER` | total_sumOfMoney_sum（3年总额）, total_trades_sum（次数）|
| STATS | 供应商分布 | POST | `bizr.../api/bizr/v1/user/trade/company/reports/0/stats` | 同 VOT + `statFields=trades,top_items,exporter` | exporter.results[]（top-10 供应商）|
| T4-LI | 社媒联系人 | GET | `bizr.../api/contactx/v3/contacts/linkedin` | `tid`, `globizId`, `linkedInCompanyId` | 真实姓名+职位+邮箱，emailVerify(WHITE/BLACK) |
| T4-NET | 邮件联系人 | GET | `bizr.../api/contactx/v3/contacts/internet` | `tid`, `website`, `taxNo` | 官网爬取邮箱，important 字段 |
| T4-MORE | 更多联系人 | GET | `bizr.../api/contactx/**v2**/contacts/more` | `tid`, `page`（从1起） | status(VALID/INVALID)，与 LI 有重叠需去重 |

**15 采集字段**（业务已确认）：公司名称、英文名称、国家、细分行业、产品标签、员工人数、官网、数据来源（固定"腾道"）、有无进出口数据、进出口总额（3年）、进出口次数、联系人数、成立时间、PCB供应商、更新时间。
→ 完整字段映射详见 `docs/research/tendata-field-mapping.md` v1.3

**联系人统一格式**（3分支合并后）：姓名、职位、邮箱、重要程度、来源描述、是否验证；去重主键 = `email`。

**原始抓包文件**：`docs/research/captures/tengdao_*.sh` + `*_response.json`（7个接口均已存档）

### 8.4 分期对 Spec 主体的影响

Spec 主体（第 1-7 节）描述的是**最终形态**。Phase 1 已交付其中绝大部分能力（外贸通直采 + 腾道反推 + 清洗），仅外贸通反推路径放到 Phase 2。代码和 schema 设计要为 Phase 2 留扩展位（外贸通 Provider 的反推路径接口、Stage 2 双路结果合并的 `clean_companies` 写入逻辑）。
