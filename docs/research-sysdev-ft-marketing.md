# 深度调研：aoqi-ai/sysdev-ft-marketing（外贸获客营销系统）

> 调研日期：2026-05-16
> 仓库地址：https://github.com/aoqi-ai/sysdev-ft-marketing（私有）

---

## 一、项目概况

| 项 | 值 |
|---|---|
| 技术栈 | Python 3.11+ / FastAPI / Prefect / psycopg2 / PostgreSQL / React 19 + TS + Ant Design v6 + Vite |
| AI 引擎 | OpenRouter LLM（主力 DeepSeek，fallback Grok/Perplexity） |
| 邮件服务 | EngageLab |
| 外部数据源 | 网易外贸通（`waimao.office.163.com`） |

---

## 二、目录结构

```
/
├── .devcontainer/           # Dev container 配置
├── .factory/                # Factory 配置
├── .github/                 # GitHub Actions
├── main_api.py              # FastAPI 服务入口
├── requirements.txt         # Python 依赖
├── api/                     # FastAPI 路由层
│   ├── __init__.py
│   ├── auth_middleware.py   # JWT 认证中间件
│   ├── deps.py              # DB 连接池 (psycopg2)
│   ├── observability.py     # 请求追踪/指标
│   ├── routes_auth.py       # 登录认证
│   ├── routes_companies.py  # 公司列表/详情
│   ├── routes_company_assets.py  # 公司资产
│   ├── routes_contacts.py   # 联系人
│   ├── routes_dashboard.py  # 仪表盘统计
│   ├── routes_drafts.py     # 邮件草稿审批
│   ├── routes_keywords.py   # 关键词 CRUD
│   ├── routes_plans.py      # 计划管理+状态机
│   ├── routes_product_config.py  # 清洗规则/行业配置
│   ├── routes_tasks.py      # 任务管理
│   └── routes_templates.py  # 邮件模板
├── flows/                   # Prefect 工作流
│   ├── config.py            # 全局常量配置
│   ├── flow_01_keyword_collect.py  # 关键词采集
│   ├── flow_02_company_analysis.py # 公司清洗+评级
│   ├── flow_03_email_draft.py      # AI 开发信生成
│   ├── flow_04_email_send.py       # 邮件发送
│   ├── main.py
│   └── utils/               # 工具模块
│       ├── auth_refresh.py
│       ├── browser_cookie.py  # Playwright 浏览器会话管理
│       ├── db.py              # PostgreSQL 连接
│       ├── email_templates.py
│       ├── email_validator.py
│       ├── engagelab.py       # EngageLab 邮件 API
│       ├── keyword_generator.py # LLM 关键词生成
│       ├── llm.py             # OpenRouter LLM 封装
│       ├── netease_api.py     # 网易外贸通 API 封装
│       ├── run_tracker.py     # flow_runs 生命周期
│       ├── timezone.py
│       └── warmup.py          # 域名预热/配额管理
├── scripts/                 # 运维脚本
│   ├── scheduler.py         # 核心调度器
│   ├── migrate_plan_schema.py
│   ├── migrate_flow_tracking.py
│   ├── migrate_template_schema.py
│   ├── migrate_email_round_schema.py
│   ├── migrate_contact_classification_v2.sql
│   ├── migrate_product_tags.py
│   ├── scheduled_collect.py
│   ├── followup_auto_sender.py
│   └── ...（导出/回填脚本）
├── web/                     # React 前端 (Vite)
│   ├── src/
│   │   ├── api/client.ts    # Axios 封装
│   │   ├── pages/           # 页面组件
│   │   ├── router/index.tsx # 路由配置
│   │   └── utils/auth.ts    # 认证工具
│   └── ...
├── tests/                   # 测试套件
└── docs/                    # 文档
```

---

## 三、采集逻辑

### 3.1 数据源 — 网易外贸通 API

系统的唯一外部数据源是网易外贸通，通过以下 API 获取数据：

| API 能力 | 用途 |
|---|---|
| 公司搜索 | 按关键词+国家搜索目标公司列表 |
| 公司详情 | 获取公司完整信息 |
| 联系人获取 | 获取公司下的联系人列表 |
| 海关数据 (BaseInfo) | 获取采购商基础海关进出口数据 |

### 3.2 认证机制

- **Playwright 持久化浏览器**管理登录态
- Cookie（`QIYE_TOKEN`、`QIYE_SESS`）存储在数据库 `system_config` 表
- API 调用使用自定义签名机制（MD5 对参数排序后拼接 secret 签名）
- 支持自动 Cookie 刷新：401 时触发 `browser_cookie.do_refresh()` 无头刷新

### 3.3 四阶段 Pipeline

#### Flow 01 — 关键词采集入库 (`flows/flow_01_keyword_collect.py`)

##### 概览

1. 从 `keyword_list` 表读取未完成关键词（`status != 'done'`）
2. 按每日配额筛选可执行关键词（`today_pages < daily_limit`）
3. 逐页调用网易搜索 API（`search_companies`），每页 100 条
4. 幂等写入 `company_data` 表（存在则合并标签/关键词，不存在则新增）
5. 回写关键词进度（`current_page`、`total_pages`、`today_pages`）
6. 限流保护：遇到 403/429 时暂停，页间随机等待 3-8 秒

关键参数：
- `MAX_PAGES_PER_RUN = 10`（单次运行每个关键词最多采集 10 页）
- `PAGE_SIZE = 100`（每页 100 条公司）
- `DAILY_API_QUOTA = 100000`（调度器层全局每日配额）

##### 完整执行流程

```
scheduler (30s扫描)
  → 发现 plan status=collecting 且有未完成关键词
  → _dispatch_plan() 启动线程
    → keyword_collect_flow(plan_id=X)
      → task_fetch_keywords: SELECT ... FROM keyword_list WHERE status<>'done'
      → task_filter_eligible_keywords: 按 daily_limit + last_run_date 筛选
      → task_load_auth: SELECT ... FROM system_config WHERE category='auth'
      → for each keyword:
          → task_process_keyword:
              → for page in range(current_page+1, ...):
                  → search_companies(keyword, country, page, 100, auth)
                  → for company in response:
                      → _upsert_company(company, keyword, plan_id)
                  → UPDATE keyword_list 进度
                  → sleep(random 3~8 秒)
      → _transition_plan_to_cleaning(plan_id)
          → 若所有关键词 done → UPDATE email_plans SET status='cleaning'
```

##### 关键词筛选逻辑

读取 SQL：
```sql
SELECT id, keyword, country, status, current_page, total_pages,
       total_results, today_pages, daily_limit, last_run_date, error_msg
FROM public.keyword_list
WHERE COALESCE(status, '') <> 'done'
  [AND plan_id = %s]
ORDER BY id
```

筛选条件（同时满足才入选）：
- `has_more_pages`：`total_pages == 0`（未开始）或 `current_page < total_pages`
- `within_today_limit`：`today_pages < daily_limit`
- 跨日重置：若 `last_run_date != today` 则 `today_pages` 视为 0

##### 网易外贸通搜索 API

请求体：
```python
{
    "searchType": "product",
    "product": keyword,        # 搜索关键词
    "page": page,              # 页码
    "size": 100,               # 每页条数
    "hasEmail": True,          # 必须有邮箱
    "hasCustomsData": True,    # 必须有海关数据
    "hasDomain": True,         # 必须有域名
    "country": ["Germany"],    # 目标国家列表
    "sortField": "default",
    "allMatchQuery": False,
    "hasBrowsed": False,
    "excludeExpressCompany": False,
    "filterEdm": False,
    "filterCustomer": False,
    "filterContactNum": False,
    "version": 1,
}
```

URL: `https://waimao.office.163.com/globalSearch/api/globalSearch/v1/search`

签名算法：`MD5(secret + sorted(key=value pairs) + secret)` 大写

重试机制：
- 网络错误：3 次重试，指数退避（3s/6s/9s）
- HTTP 401：自动触发 Playwright 无头浏览器刷新 Cookie（60 秒冷却）
- HTTP 403/429：标记 `status='paused'`，终止整个 flow
- 请求超时：30 秒

##### 幂等写入逻辑 `_upsert_company()`

**查重 SQL**（按 company_id + plan_id）：
```sql
-- 有 plan_id 时
SELECT id, source_tags, source_keyword, source_competitor, api_company_id
FROM public.company_data
WHERE company_id=%s AND (plan_id=%s OR plan_id IS NULL)
ORDER BY CASE WHEN plan_id=%s THEN 0 WHEN plan_id IS NULL THEN 1 ELSE 2 END, id
LIMIT 1

-- 无 plan_id 时
SELECT ... FROM public.company_data WHERE company_id=%s AND plan_id IS NULL LIMIT 1
```

**已存在 → UPDATE（合并）**：
```sql
UPDATE public.company_data
SET company_name=%s, country=%s, domain=%s, source_type=%s,
    source_keyword=%s, source_competitor=%s, real_id=%s, id_verified=%s,
    raw_data=%s, source_tags=%s, plan_id=COALESCE(plan_id, %s),
    api_company_id=%s, updated_at=NOW()
WHERE id=%s
```

合并规则：
- `source_keyword`：追加当前 keyword（逗号分隔，去重）
- `source_tags`：合并新旧标签列表（去重）
- `source_type`：含"采购商"标签→buyer，含"同行"→competitor，否则 search
- `api_company_id`：取新值或保留旧值

**不存在 → INSERT**：
```sql
INSERT INTO public.company_data
    (company_id, company_name, country, domain,
     source_type, source_keyword, source_competitor, real_id,
     id_verified, raw_data, source_tags, api_company_id,
     plan_id, sys_company_id, created_at, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, gen_random_uuid(), NOW(), NOW())
```

##### API 响应 → DB 字段映射

| API 字段 | DB 字段 | 变换规则 |
|---|---|---|
| `id` 或 `domain` | `company_id` | 取 id 优先，domain 兜底 |
| `name` 或 `recommendShowName` | `company_name` | 直接取 |
| `country` | `country` | 直接取 |
| `domain` | `domain` | 直接取 |
| `id` | `api_company_id` | 原始 API ID |
| `realId` 或 `real_id` | `real_id` | 直接取 |
| tags/tagList/sourceTags/labels | `source_tags` | JSON array，多字段提取合并 |
| 整个 company dict | `raw_data` | 完整 JSON 保存 |
| — | `sys_company_id` | `gen_random_uuid()` 自动生成 |
| 推断自 tags | `source_type` | buyer/competitor/search |

##### 标签提取 `_extract_tags()`

从 API 返回的公司对象中依次检查 key：`tags`, `tagList`, `sourceTags`, `source_tags`, `labels`

支持格式：
- `list[dict]` → 取 `name` 或 `label` 字段
- `list[str]` → 直接用
- `str` → 尝试 JSON parse，否则逗号分割

##### 进度追踪字段

| 字段 | 含义 | 更新时机 |
|---|---|---|
| `current_page` | 已完成的最大页码 | 每页处理完 |
| `total_pages` | 总页数（`ceil(total/100)`） | 首次 API 返回后 |
| `total_results` | API 返回的总结果数 | 首次 API 返回后 |
| `today_pages` | 今日已处理页数 | 每页处理完 +1 |
| `daily_limit` | 每日最大可处理页数 | 关键词创建时设定（默认10） |
| `last_run_date` | 上次执行日期 | 每页处理完 |
| `status` | running/done/pending/paused/error | 每个关键词处理完 |

##### 关键词自动生成 (`flows/utils/keyword_generator.py`)

输入：`country`（中文）+ `industry`（行业名）

生成规则：
1. 中文国家名 → 英文（如 "德国" → "Germany"）
2. 行业名 → 英文术语列表（精确匹配 + 分隔符拆分 + DB 配置兜底）
3. 每个术语 × 4 个后缀：`manufacturer`, `factory`, `producer`, `supplier`
4. 组合格式：`[Country] [term] [suffix]`，如 `Germany PCB manufacturer`
5. 全部去重（case-insensitive），`status='pending'`，`daily_limit=10`

##### 计划状态推进

```sql
-- 检查是否还有未完成关键词
SELECT COUNT(*) FROM public.keyword_list
WHERE plan_id=%s AND COALESCE(status, '') <> 'done'

-- 全部 done → 推进到 cleaning
UPDATE email_plans SET status='cleaning', updated_at=NOW()
WHERE id=%s AND status='collecting'
```

##### 调度器触发条件

- 计划处于 `keyword_gen` 或 `collecting` 状态
- 存在未完成关键词（`status <> 'done'`）
- 每日配额未耗尽（估算 API cost）
- 同一 (plan_id, stage) 无活跃线程
- 双重防重复：内存 `_running_tasks` + DB `flow_runs WHERE status='running'`

##### 设计总结

| 维度 | 实现方式 |
|---|---|
| 幂等写入 | 按 `company_id + plan_id` 查重，存在则 UPDATE 合并，不存在则 INSERT |
| 断点续传 | `current_page` 持久化到 DB，下次从 `current_page+1` 继续 |
| 每日配额 | `today_pages` + `daily_limit` + `last_run_date`，跨日自动重置 |
| Rate limiting | 每页间 random(3,8)秒；403/429 标记 paused 终止 flow |
| 重试 | 网络层 3 次（指数退避）；401 自动刷新 Cookie |
| 超时 | HTTP 30秒；Scheduler watchdog 60分钟 |
| 错误隔离 | 单个关键词失败不影响其他（try/except 包裹） |
| 计划推进 | 所有关键词 done → 自动 collecting → cleaning |
| 配额管控 | Scheduler 估算 API cost，超出每日 10万则跳过 |

#### Flow 02 — 公司清洗评估 (`flows/flow_02_company_analysis.py`)

1. 查询 `company_data` 中未清洗的公司
2. 调用 LLM（主模型：`x-ai/grok-4.1-fast`，fallback：`perplexity/sonar` → `deepseek/deepseek-chat`）进行行业分析
3. 按 16 个 PCB 细分行业分类：A 级（精确命中）/ B 级（PCB 相关）/ X 级（无关丢弃）
4. 多维度评分：相关性(40分) + 市场匹配度(30分) + 采购意向(30分)
5. A/B 级公司自动获取详情+联系人+海关数据（调用网易 API）
6. 结果写入 `company_analysis` 表

##### Flow 02 数据存储详解

清洗过程涉及 **4 个表**，数据流向：

```
company_data (读取待分析公司)
    ↓
company_analysis (UPSERT 清洗结果)
    ↓ 仅 A/B 级触发
company_detail (UPSERT 公司详情)
contact_data (INSERT 去重联系人)
    ↓ 同时回写
company_data (UPDATE 元数据标记)
```

**写入表 1：`company_analysis`（主结果表，UPSERT）**

冲突键：`(sys_company_id, plan_id)`

A/B 级公司写入 30+ 字段：

| 类别 | 字段 |
|---|---|
| LLM 分析 | `grade`, `score`, `sub_industry`, `product_tags(jsonb)`, `score_details(jsonb)`, `match_reasons`, `potential_needs`, `recommended_products`, `risk_factors` |
| 公司画像 | `english_name`, `website`, `region`, `founded_year`, `company_size`, `revenue_estimate`, `industry`, `main_business`, `company_type` |
| 关联/状态 | `sys_company_id`, `plan_id`, `email_priority='selected'` |
| 原始存档 | `search_raw`（原始 JSON）, `ai_raw`（LLM 完整输出）, `data_sources` |
| 贸易数据 | `has_trade_data`, `trade_summary(jsonb)` |

X 级公司仅写最小记录：`grade='X', score=0, email_priority='skipped'`

**写入表 2：`company_data`（回写元数据标记，不动核心字段）**

```sql
UPDATE company_data
SET has_detail=true, has_contacts=..., contact_count=...,
    api_company_id=..., id_verified=true,
    detail_status='completed', updated_at=NOW()
WHERE sys_company_id=%s
```

**写入表 3：`company_detail`（仅 A/B 级，UPSERT）**

从网易外贸通 API 获取完整公司详情：

| 字段 | 来源 |
|---|---|
| `full_address` | `detail.address` 或 `detail.location` |
| `website` | `detail.domain` |
| `phone` | `detail.phone` |
| `industry` | `detail.industry` |
| `employee_size` | `detail.employeeSize` |
| `founded_year` | `detail.foundedYear` |
| `description` | `detail.overviewDescription` |
| `products` | `detail.productList[*].name` 拼接 |
| `raw_data` | 完整 API 响应 JSON |

**写入表 4：`contact_data`（仅 A/B 级，INSERT 去重）**

三级去重逻辑：按 `contact_id` → `email` → `name+position` 检查，不存在才 INSERT。

| 字段 | 来源 |
|---|---|
| `sys_contact_id` | `gen_random_uuid()` 自动生成 |
| `contact_id` | API 返回的 `id` 或 `contactId` |
| `name` | `contact.name` |
| `position` | `contact.position` 或 `contact.jobTitle` |
| `department` | `contact.department` |
| `email` | `contact.emails[0].email` 或回退 `contact.contact` |
| `email_status` | `contact.emailStatus` |
| `phone` / `mobile` | `contact.phone` / `contact.cellphone` |
| `linkedin` / `whatsapp` | `contact.linkedin` / `contact.whatsapp` |
| `source` | `contact.source` 或默认 `"netease"` |
| `confidence` | `contact.confidence` |
| `raw_data` | 单条联系人完整 JSON |

##### 前端读取对应关系

| API 端点 | 查询的表 | 含义 |
|---|---|---|
| `GET /api/company-assets` | `company_data` | 原始采集资产（标记 `is_analyzed`） |
| `GET /api/companies` | `company_analysis` | 清洗后公司（默认 score DESC） |
| `GET /api/contacts` | `contact_data` | 联系人列表 |

三表通过 **`sys_company_id`**（UUID）关联。

#### Flow 03 — AI 开发信生成 (`flows/flow_03_email_draft.py`)

1. 查找已清洗且 `email_priority='selected'` 的公司的联系人
2. 使用 LLM（`deepseek/deepseek-chat`）生成个性化外贸开发信
3. 根据国家自动选择语言、邮件模板
4. 生成结果存入 `email_drafts` 表（`send_status='draft'`）

#### Flow 04 — 邮件发送 (`flows/flow_04_email_send.py`)

1. 查询已审批（`send_status='approved'`）且处于目标国家工作时间的草稿
2. 调用 EngageLab API 发送邮件
3. 回写发送状态和时间
4. 支持域名预热配额控制（5→2500封，20天预热周期）

### 3.4 调度器 (`scripts/scheduler.py`)

- **每 30 秒**扫描一次活跃计划（排除 `draft`/`done`）
- 按 **priority DESC** 顺序分配每日 API 配额（10万/天）
- 根据计划状态自动派发对应 Flow（多线程并行）
- 支持并行流水线：同一计划可同时运行 collecting + cleaning + generating + sending
- 优雅关闭：SIGTERM/SIGINT → 等待运行中 flow 完成（最长 60 秒）

计划状态机：
```
draft → approved → keyword_gen → collecting → cleaning → generating → pending_approval → sending → done
```

### 3.5 端到端采集流程图

```
[用户创建计划] → 设置国家+行业+优先级
       ↓ (人工审批)
[approved] → 调度器触发 keyword_generator → LLM 自动生成关键词 → keyword_list
       ↓
[keyword_gen/collecting] → Flow 01 → 调用网易搜索 API → company_data (逐页采集,随机间隔)
       ↓ (所有关键词采完)
[cleaning] → Flow 02 → LLM 分析分类(A/B/X) + 网易获取详情/联系人 → company_analysis + contact_data
       ↓ (清洗完毕)
[generating] → Flow 03 → LLM 生成个性化开发信 → email_drafts (status=draft)
       ↓ (人工审批草稿)
[sending] → Flow 04 → EngageLab API 发送 → 回写 sent_at
       ↓ (全部发完)
[done]
```

---

## 四、数据存储逻辑

### 4.1 数据库

PostgreSQL，通过 psycopg2 直连（无 ORM），环境变量配置：`FT_DB_HOST`、`FT_DB_PORT`、`FT_DB_USER`、`FT_DB_NAME`

### 4.2 核心数据表

| 表名 | 用途 | 关键字段 |
|---|---|---|
| `email_plans` | 营销计划 | id, plan_name, country, industry, status, priority, round_number, linked_plan_id, interval_days |
| `keyword_list` | 关键词库 | id, keyword, country(jsonb), status, current_page, total_pages, today_pages, daily_limit, last_run_date, plan_id |
| `company_data` | 采集的原始公司数据 | id, company_id, company_name, country, domain, source_type, source_keyword, source_competitor, source_tags, raw_data, api_company_id, real_id, id_verified, sys_company_id(uuid), plan_id |
| `company_analysis` | 清洗/分析结果 | id, company_id, sys_company_id, company_name, english_name, country, grade, score, sub_industry, classification, product_tags(jsonb), score_details(jsonb), email_priority, plan_id, search_raw, ai_raw, has_trade_data, trade_summary(jsonb) |
| `company_detail` | 公司详情（API补全） | id, sys_company_id, api_company_id, full_address, website, phone, industry, employee_size, founded_year, description, products, raw_data |
| `contact_data` | 联系人 | id, contact_id, company_id, sys_contact_id, sys_company_id, api_company_id, name, position, department, email, email_status, phone, mobile, linkedin, whatsapp, source, confidence, raw_data |
| `email_drafts` | 邮件草稿 | id, sys_company_id, sys_contact_id, plan_id, round_number, send_status, subject, body, sent_at, review_note |
| `email_templates` | 邮件模板 | id, name, subject_template, body_template, round_number, language, country, industry, is_active |
| `flow_runs` | 流程运行记录 | id, flow_id, flow_name, status, started_at, finished_at, result(jsonb), error_message |
| `scheduled_tasks` | 定时任务配置 | id, flow_id, flow_name, cron_expression, enabled, parameters(jsonb), last_run_at, next_run_at |
| `system_config` | 系统配置(认证/凭证) | key, value, category |
| `product_industry_config` | 产品行业配置 | id, name, description, keywords, enabled, sort_order |
| `draft_rewrite_logs` | AI 重写审计日志 | draft_id, instruction, old_body, new_body, created_at |

### 4.3 关键索引和约束

- `company_data` 按 `company_id` + `plan_id` 实现幂等写入
- `company_analysis` 有条件唯一索引：`(company_id) WHERE plan_id IS NULL` 和 `(company_id, plan_id) WHERE plan_id IS NOT NULL`
- `email_drafts` 复合唯一键：`(sys_contact_id, round_number)`
- 所有业务表都有 `plan_id` 外键关联到 `email_plans`
- `email_plans.status` 有 CHECK 约束限制 9 个有效状态

### 4.4 视图

- `v_buyer_contacts` — 联系人分级视图，使用 `classify_contact()` 函数将联系人按职位分为 A（老板/高管/采购/进出口）和 B（工程/生产/项目经理）级

### 4.5 配置存储（`system_config` 表）

| key | 用途 |
|---|---|
| `auth.qiye_token` / `auth.qiye_sess` | 网易外贸通认证 Cookie |
| `auth.device_id` / `auth.secret_key` | API 签名密钥 |
| `llm.openrouter_api_key` | LLM API Key |
| `mail.engagelab_api_user` / `mail.engagelab_api_key` / `mail.engagelab_sender` | 邮件服务凭证 |
| `mail.daily_limit` | 全局每日发送上限 |

---

## 五、前端展示逻辑

### 5.1 完整 API 端点

#### 认证 (`api/routes_auth.py`, prefix: `/api/auth`)

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/auth/login` | JWT 登录，返回 access_token |

#### 关键词管理 (`api/routes_keywords.py`, prefix: `/api/keywords`)

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/keywords` | 列表（支持 status/plan_id/search/分页） |
| GET | `/api/keywords/{keyword_id}` | 获取单个关键词 |
| POST | `/api/keywords` | 创建关键词 |
| PUT | `/api/keywords/{keyword_id}` | 更新关键词 |
| DELETE | `/api/keywords/{keyword_id}` | 删除关键词 |

#### 公司资产库 (`api/routes_company_assets.py`, prefix: `/api/company-assets`)

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/company-assets` | 列表（支持 country/source_type/has_detail/has_contacts/search/plan_id/分页） |
| GET | `/api/company-assets/stats` | 统计（总数、按国家、按来源类型、已分析数） |
| GET | `/api/company-assets/filters` | 筛选器下拉选项（国家、来源类型） |

#### 公司列表 (`api/routes_companies.py`, prefix: `/api/companies`)

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/companies` | 列表（清洗后，支持 country/grade/plan_id/sub_industry/product_tags/search/分页） |
| GET | `/api/companies/{company_id}` | 获取公司详情 |

#### 联系人 (`api/routes_contacts.py`, prefix: `/api/contacts`)

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/contacts` | 列表（支持 company_id/plan_id/email_status/search/分页） |
| GET | `/api/contacts/{contact_id}` | 获取联系人详情 |
| GET | `/api/contacts/buyer` | 清洗后买家联系人列表（带 priority/category 分类） |
| GET | `/api/contacts/buyer/filters` | 买家联系人筛选选项 |

#### 计划管理 (`api/routes_plans.py`, prefix: `/api/plans`)

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/plans` | 列表（支持 status/search/分页） |
| GET | `/api/plans/{plan_id}` | 获取单个计划 |
| GET | `/api/plans/{plan_id}/preview` | 预览计划目标集 |
| GET | `/api/plans/{plan_id}/sending-preview` | 预览发送排期 |
| GET | `/api/plans/{plan_id}/progress` | 获取计划进度指标 |
| POST | `/api/plans` | 创建计划 |
| PUT | `/api/plans/{plan_id}` | 更新计划 |
| POST | `/api/plans/{plan_id}/transition` | 状态流转 |
| POST | `/api/plans/{plan_id}/approve` | 审批计划 |
| POST | `/api/plans/{plan_id}/approve-drafts` | 批量审批该计划下所有草稿 |
| POST | `/api/plans/{plan_id}/reject` | 驳回计划 |
| POST | `/api/plans/{plan_id}/assign-companies` | 分配公司到计划 |
| POST | `/api/plans/{plan_id}/select-companies` | 选择/跳过公司 |
| POST | `/api/plans/{plan_id}/trigger/{flow_name}` | 手动触发 Flow |
| DELETE | `/api/plans/{plan_id}` | 删除计划 |

#### 邮件模板 (`api/routes_templates.py`, prefix: `/api/templates`)

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/templates` | 列表（支持 round_number/language/is_active/country/industry/分页） |
| GET | `/api/templates/{template_id}` | 获取模板 |
| GET | `/api/templates/{template_id}/preview` | 预览渲染后的模板 |
| POST | `/api/templates` | 创建模板 |
| PUT | `/api/templates/{template_id}` | 更新模板 |
| DELETE | `/api/templates/{template_id}` | 删除模板 |

#### 邮件草稿 (`api/routes_drafts.py`, prefix: `/api/drafts`)

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/drafts` | 列表（支持 send_status/country/plan_id/search/分页） |
| GET | `/api/drafts/{draft_id}` | 获取草稿 |
| POST | `/api/drafts/{draft_id}/approve` | 审批草稿 |
| POST | `/api/drafts/{draft_id}/rewrite` | AI 重写（DeepSeek） |
| GET | `/api/drafts/{draft_id}/rewrite-history` | 重写历史记录 |

#### 清洗规则配置 (`api/routes_product_config.py`, prefix: `/api/product-config`)

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/product-config` | 列表所有产品配置 |
| POST | `/api/product-config` | 创建配置 |
| PUT | `/api/product-config/{config_id}` | 更新配置 |
| DELETE | `/api/product-config/{config_id}` | 删除配置 |
| POST | `/api/product-config/reorder` | 重新排序 |
| GET | `/api/product-config/scoring-template` | 获取 LLM prompt 评分模板 |

#### 任务监控 (`api/routes_tasks.py`, prefix: `/api`)

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/task-runs` | 列表 Flow 运行记录（支持 flow_id/status/分页） |
| GET | `/api/task-runs/latest` | 各 Flow 最近运行状态 |
| POST | `/api/task-runs/{run_id}/stop` | 停止运行中的任务 |
| POST | `/api/task-runs/trigger/{flow_id}` | 手动触发 Flow |
| GET | `/api/scheduled-tasks` | 列表定时任务 |
| PUT | `/api/scheduled-tasks/{flow_id}` | 更新定时任务配置 |

#### 仪表盘 (`api/routes_dashboard.py`, prefix: `/api/dashboard`)

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/dashboard/overview` | 全局概览（漏斗、分布、趋势） |
| GET | `/api/dashboard/stats` | 统计数据 |
| GET | `/api/dashboard/llm-balance` | OpenRouter LLM 余额 |
| GET | `/api/dashboard/daily-quota` | 每日邮件配额 |
| GET | `/api/dashboard/plan-overview` | 按计划的概览统计 |
| GET | `/api/dashboard/engagelab-stats` | EngageLab 邮件投递统计 |

#### 健康检查（`main_api.py`）

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/` | 服务状态 |
| GET | `/health` | 健康检查（含 DB 连通性） |
| GET | `/metrics` | 指标 |

### 5.2 前端页面结构

| 路由 | 页面 | 调用的 API | 展示内容 |
|---|---|---|---|
| `/` | 首页仪表盘 | dashboard/engagelab-stats, llm-balance, daily-quota, plan-overview, plans | EngageLab 邮件统计、LLM 余额、配额、漏斗进度 |
| `/plans` | 计划管理 | plans, plans/{id}/progress | 计划列表表格（状态、进度、轮次标签） |
| `/plans/:id` | 计划详情 | plans/{id}, progress, keywords, companies, drafts | 进度 pipeline、关键词/公司/草稿 Tab |
| `/keywords` | 关键词管理 | keywords, plans | 关键词表格（状态、配额、计划归属） |
| `/company-assets` | 公司资产库 | company-assets, stats, filters | 原始采集公司表格+统计概览 |
| `/companies` | 公司列表 | companies | 清洗后公司（评分、等级、行业、标签） |
| `/contacts` | 联系人 | contacts, contacts/buyer | 全部联系人 + 买家联系人 Tab |
| `/templates` | 邮件模板 | templates, preview | 模板表格 + 预览渲染 |
| `/drafts` | 草稿审核 | drafts, approve, rewrite, rewrite-history | 草稿列表、审批、AI 重写 |
| `/cleaning-rules` | 清洗规则 | product-config | 产品行业配置、拖拽排序 |
| `/tasks` | 任务监控 | task-runs, scheduled-tasks | 运行历史、手动触发/停止 |

### 5.3 前端 API 客户端 (`web/src/api/client.ts`)

- 基于 `axios` 创建，baseURL 从 `VITE_API_BASE` 读取（默认 `http://localhost:8000`）
- 请求拦截器：自动附加 `Authorization: Bearer <token>` 和 `X-Request-ID`
- 响应拦截器：401 清除 token 跳转 `/login`；错误上报 Sentry
- 封装 `apiGet<T>()`, `apiPost<T, B>()`, `apiPut<T, B>()`, `apiDelete<T>()` 泛型函数

### 5.4 数据流：从存储到显示

```
PostgreSQL 数据库
    │
    │ psycopg2 直连（api/deps.py: fetch_all/fetch_one/execute/execute_returning）
    ▼
FastAPI 路由层（api/routes_*.py）
    - 接收 HTTP 请求，参数校验（Pydantic）
    - 执行 SQL 查询，返回 JSON
    │
    │ HTTP/JSON (CORS: allow_origins=["*"])
    ▼
Axios API 客户端（web/src/api/client.ts）
    - Bearer Token 认证
    - 统一错误处理
    │
    ▼
React 页面组件（web/src/pages/*.tsx）
    - useEffect + useState 获取数据
    - Ant Design Table/Card/Statistic 渲染
    - 表格支持分页、筛选、搜索
```

## 
