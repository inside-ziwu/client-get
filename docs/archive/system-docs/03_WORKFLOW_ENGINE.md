# 工作流引擎 - Prefect Flows 与调度器

> 核心路径: `flows/` + `scripts/scheduler.py`
> 引擎: Prefect 3.6.21

---

## 1. 架构概览

```
scheduler.py (每30秒循环)
    │
    ├── 扫描活跃计划 (email_plans WHERE status NOT IN ('draft','done'))
    ├── 检测可执行阶段
    ├── 估算API配额
    └── 派发Flow (daemon thread)
         │
         ├── Flow01: keyword_collect_flow    → 网易外贸通 Search API
         ├── Flow02: company_analysis_flow   → OpenRouter LLM + 网易外贸通 Detail/Contact API
         ├── Flow03: email_draft_flow        → OpenRouter LLM
         └── Flow04: email_send_flow         → EngageLab API
```

---

## 2. Flow 01: 关键词采集

**文件**: `flows/flow_01_keyword_collect.py`
**入口**: `keyword_collect_flow(max_pages_per_keyword=10, page_size=100, plan_id=None)`

### 执行步骤

1. 查询 `keyword_list` 中 `status != 'done'` 的关键词
2. 检查每日配额：若 `last_run_date != today`，重置 `today_pages = 0`
3. 逐个处理关键词：
   - 设置 `status='running'`
   - 循环翻页调用网易外贸通 Search API（每页100条）
   - 每条公司数据 UPSERT 到 `company_data`（按 `company_id + plan_id` 去重）
   - 合并 source_tags 和 source_keyword（追加式去重）
   - 更新进度：`current_page`, `total_pages`, `today_pages`
   - 页间随机休眠 3-8 秒
4. 完成后设置关键词 `status='done'`（全部页采完）或 `status='pending'`（还有剩余）
5. 若计划下所有关键词 done，自动转换计划状态 `collecting → cleaning`

### 速率控制
- 每页间 3-8 秒随机间隔
- 每关键词每日限制 `daily_limit` 页（默认10页）
- 单次运行最多 `MAX_PAGES_PER_RUN=10` 页/关键词
- HTTP 403/429 自动暂停

### 重试策略
- 网络层：3次重试，退避 `attempt * 3` 秒
- Flow 层：无 Prefect 级重试
- 错误隔离：单个关键词失败不影响其他

### 数据流
```
keyword_list → [网易外贸通 Search API] → company_data
```

---

## 3. Flow 02: 公司清洗评级

**文件**: `flows/flow_02_company_analysis.py`
**入口**: `company_analysis_flow(batch_limit=300, plan_id=None, country=None)`

### 执行步骤

1. 加载 `product_industry_config`（16类PCB细分行业）
2. 查询未分析公司：`company_data LEFT JOIN company_analysis`，排除中国公司
3. **5并发** 处理（`ConcurrentTaskRunner`）：

   **a) LLM 分析**:
   - 构建 Prompt：公司信息 + 行业配置 + 评分标准
   - 调用 `call_llm_with_fallback()` 获取结构化 JSON
   - 解析：等级(A/B/X)、综合评分(0-100)、三维评分(relevance/market_fit/intent)
   - 规范化 `sub_industry`，匹配配置中的16类
   - UPSERT 到 `company_analysis`

   **b) A/B级公司富集**（合并了原 Flow03 的功能）:
   - 通过 BaseInfo API 补全 `company_id`
   - 获取公司详情（Detail API）→ `company_detail`
   - 获取联系人（Contact API）→ `contact_data`
   - 获取贸易数据（BaseInfo API）→ `company_analysis.trade_summary`

   **c) X级处理**:
   - 写入最小记录，`email_priority='skipped'`
   - 避免重复分析

4. 计划所有公司分析完成后，自动 `cleaning → generating`

### LLM 评分标准
```
- relevance (满分40): 产品相关性
- market_fit (满分30): 市场匹配度
- intent (满分30): 购买意向

等级划分:
- A (exact_match): score 80-100, 精准客户
- B (pcb_related): score 40-60, 相关客户
- X (unrelated):   score 0, 不相关
```

### 速率控制
- 网易API: 全局 RPM 限制器（deque + lock），15次/分钟
- API调用间 1-2 秒随机间隔
- LLM: 5并发，无显式限速

### 重试策略
- Prefect 任务级: retries=1, retry_delay=5s
- LLM: 3次重试，退避 `attempt * 5` 秒
- LLM 降级: 主模型失败后尝试 `LLM_FALLBACK_MODELS` 列表
- 网易API: 3次重试 + 401时自动刷新Cookie

### 数据流
```
company_data → [LLM分析] → company_analysis
            → [网易Detail/Contact API] → company_detail + contact_data
```

---

## 4. Flow 03: 邮件生成

**文件**: `flows/flow_03_email_draft.py`
**入口**: `email_draft_flow(batch_limit=200, plan_id=None)`

### 执行步骤

1. **解析轮次上下文**: 读取 `round_number`, `linked_plan_id`, `interval_days`
2. **筛选候选联系人**（复杂SQL，按模式分支）:
   - **跟进轮(round>=2)**: 上一轮已发送 + 间隔天数已到 + 本轮无草稿
   - **首轮(round=1)**: A/B级 + email_priority='selected' + 无已有草稿
   - **无计划模式**: v_buyer_contacts 视图，A/B优先级
   - **通用过滤**: 排除功能性邮箱（abuse, admin, info, noreply...），邮箱格式验证
3. **邮箱验证**: 语法检查 + DNS MX记录查询
4. **12并发** 生成:
   - 根据国家检测语言（`COUNTRY_LANGUAGE` 映射）
   - **模板级联匹配**: 国家+行业+轮次+语言 → 国家+轮次+语言 → 行业+轮次+语言 → 轮次+语言 → 英文兜底
   - LLM Prompt: 严格遵循模板，仅替换 `{Name}` 占位符
   - 生成 `{subject, body_target, body_zh}`
   - LLM 失败时: 直接模板变量替换作为兜底
   - 追加公司邮件签名
   - INSERT `email_drafts`，`ON CONFLICT (sys_contact_id, round_number) DO NOTHING`
5. **跟进自动发送**: round>=2 的草稿自动转计划状态为 `'sending'`

### 被过滤的功能性邮箱前缀
```
abuse, admin, billing, compliance, contact, feedback, finance, 
general, hello, help, hr, info, jobs, legal, marketing, media, 
news, noreply, no-reply, office, operations, postmaster, press, 
privacy, purchase, reception, recruit, registrar, sales, security, 
service, shop, spam, subscribe, support, team, tech, webmaster
```

### 数据流
```
contact_data + company_analysis + email_templates → [LLM生成] → email_drafts
```

---

## 5. Flow 04: 邮件发送

**文件**: `flows/flow_04_email_send.py`
**入口**: `email_send_flow(batch_size=DEFAULT_BATCH_SIZE, plan_id=None)`

### 执行步骤

1. **自动审批过期草稿**（仅无计划模式）: draft 超过24小时自动升为 approved
2. **检查预热配额**: `global_daily_limit - sent_today`，为0则跳过
3. **时区感知筛选**:
   - 按国家分组已审批草稿
   - 检查每个国家的本地时间是否在工作时间（工作日 9:00-17:00）
   - 仅对在工作时间的国家发送
4. **审批门控**:
   - `send_status='approved'`（单独审批），或
   - `send_status='draft'` 且计划 `approval_status='approved'`（批量审批）
5. **顺序发送**:
   - 纯文本转 HTML（段落格式化、签名处理）
   - 调用 EngageLab API 发送
   - 成功: `send_status='sent'`, 记录 `sent_at`
   - 失败: `send_status='failed'`, 记录错误
   - EngageLab 配额超限(code 30904): 停止发送
6. **每日监控**: 向配置的 `DAILY_RECIPIENTS` 发送随机一封审批邮件（每地址每天最多1封）
7. **完成检测**: 无剩余可发送草稿时，计划 → `'done'`

### 预热机制（Warmup）
```python
WARMUP_SCHEDULE = {
    1: 50,   2: 50,   3: 100,  4: 100,  5: 150,
    6: 150,  7: 200,  8: 200,  9: 300,  10: 300,
    11: 400, 12: 400, 13: 500, 14: 500, ...
}
```
- 从 `WARMUP_START_DATE` 开始计算第几天
- 每日发送上限按天数递增

### 重试策略
- Prefect 任务级: retries=2, retry_delay=10s
- EngageLab: 3次重试，退避 `attempt * 5` 秒

### 数据流
```
email_drafts (approved) → [EngageLab API] → email_drafts (sent/failed)
```

---

## 6. 调度器详解

**文件**: `scripts/scheduler.py`

### 核心循环（每30秒）

```python
while not stop_event.is_set():
    plans = get_active_plans()  # status NOT IN ('draft','done')
    plans.sort(key=priority DESC, id ASC)
    
    for plan in plans:
        stages = _get_applicable_stages(plan)  # 检测数据条件
        for stage in stages:
            if not _is_already_running(plan, stage):
                cost = _estimate_api_cost(plan, stage)
                if cost <= remaining_quota:
                    _dispatch(plan, stage)
                    remaining_quota -= cost
    
    sleep(30)
```

### 阶段检测逻辑

| 计划状态 | 可执行阶段 | 条件 |
|----------|-----------|------|
| approved (非跟进) | keyword_gen | 首次进入 |
| collecting | Flow01 | 有 pending 关键词 |
| cleaning | Flow02 | 有未分析的公司 |
| generating | Flow03 | 有未生成草稿的联系人 |
| sending | Flow04 | 有已审批的草稿 |

### 配额管理

- **每日总额**: 100,000 次 API 调用
- **成本估算**:
  - Flow01: 剩余页数
  - Flow02: 未清洗公司数 × 3（detail + contacts + baseinfo）
  - Flow03/04: 0（LLM/EngageLab 不计入网易配额）
- **跟踪**: `flow_runs.result.api_quota_allocated`

### 安全机制

| 机制 | 说明 |
|------|------|
| 去重保护 | 内存 `_running_tasks` + 数据库 `flow_runs` 双重检查 |
| 超时看门狗 | 每个 Flow 配60分钟超时的守护线程 |
| 优雅关停 | SIGTERM/SIGINT → 设置停止事件 → 等待60秒 |
| 残留清理 | 启动时将超时的 `running` 状态标记为 `failed` |
| Prefect维护 | 每日自动 VACUUM SQLite 数据库（>1GB时） |

---

## 7. 工具模块

### `flows/utils/db.py` - 数据库
- `get_conn()`: 上下文管理器，30秒语句超时
- `fetch_all/fetch_one/execute/execute_returning`: 标准 CRUD 封装

### `flows/utils/netease_api.py` - 网易外贸通
- MD5 签名认证
- 4个端点: search, detail, contacts, base_info
- 401 自动刷新 Cookie（headless browser）
- 全局 RPM 限制器（15次/分钟）

### `flows/utils/llm.py` - OpenRouter LLM
- 3次重试 + 降级模型列表
- JSON 响应解析: 直接解析 → 修复转义 → 提取首个 `{...}` 块

### `flows/utils/engagelab.py` - EngageLab 邮件
- Basic Auth 认证
- 纯文本→HTML 转换
- 3次重试

### `flows/utils/email_validator.py` - 邮箱验证
- 正则语法检查
- DNS MX 记录验证

### `flows/utils/warmup.py` - 域名预热
- 渐进式每日配额
- 已发送计数查询

### `flows/config.py` - 全局配置
- API URL 常量
- 国家→时区映射
- 国家→语言映射
- 预热调度表
- 功能性邮箱前缀黑名单

---

## 8. 产品化标注

| 现状 | 产品化需求 |
|------|-----------|
| 硬编码 PCB 行业 Prompt | 租户自定义 Prompt 模板 |
| 单一调度器进程 | 分布式任务队列（Celery/分布式 Prefect） |
| 所有计划共享配额 | 租户级配额隔离 |
| 网易外贸通 Cookie 共享 | 租户各自配置数据源凭证 |
| 无回调/Webhook | 状态变更通知机制 |
| 60分钟硬超时 | 可配置超时 + 断点续跑增强 |
