# 外部集成依赖分析

> 文档版本：v1.0 | 基于仓库 aoqi-ai/sysdev-ft-marketing | 2026-04-16
> 用途：供 AI Agent 上下文注入 + 人类开发者参考

---

## 概览

系统依赖 **3 个外部服务**完成核心业务链路：

```
网易外贸通 ──→ 公司搜索 + 联系人获取
OpenRouter ──→ AI 公司评级 + 邮件生成
EngageLab  ──→ 邮件发送 + 数据追踪
```

| 外部服务 | 用途 | 调用频率 | 可替换性 | 业务关键度 |
|----------|------|----------|----------|------------|
| 网易外贸通 | 数据采集 | ~15 RPM | 中（可扩展其他数据源） | ⬤⬤⬤ 核心 |
| OpenRouter | LLM 推理 | ~5 并发 | 高（标准 OpenAI 兼容接口） | ⬤⬤⬤ 核心 |
| EngageLab | 邮件投递 | ~50/批次 | 中（需评估替代方案送达率） | ⬤⬤⬤ 核心 |

---

## 1. 网易外贸通（公司数据采集）

### 1.1 基本信息

| 项目 | 值 |
|------|-----|
| **服务提供商** | 网易（NetEase） |
| **产品名** | 外贸通 / WaimaoPass |
| **基础 URL** | `https://waimao.office.163.com` |
| **认证方式** | Cookie + MD5 签名 |
| **代码位置** | `flows/utils/netease_api.py`（248行）, `flows/utils/auth_refresh.py`（540行）, `flows/utils/browser_cookie.py`（222行） |
| **配置位置** | `flows/config.py` |

### 1.2 API 端点

| 端点 | HTTP | 路径 | 用途 | 调用者 |
|------|------|------|------|--------|
| **公司搜索** | POST | `/openapi/search/company/search` | 按关键词分页搜索海外公司 | Flow 01 |
| **公司详情** | POST | `/openapi/search/company/detail` | 获取公司完整信息 | Flow 02 |
| **联系人** | POST | `/openapi/search/company/contact` | 获取公司联系人列表 | Flow 02 |
| **基本信息** | POST | `/openapi/search/company/baseInfo` | 获取公司基本信息 | Flow 02 |

### 1.3 认证机制

**三层认证体系**（复杂度高，是系统最脆弱的外部依赖点）：

```
Layer 1: Cookie 认证
├── 通过网易邮箱账号登录获取 Cookie
├── Cookie 存储在 DB 表 system_config (key='netease.cookies')
└── 过期后需重新登录

Layer 2: MD5 请求签名
├── 每个请求附带 timestamp + token
├── token = MD5(sorted_params + cookie_token)
└── 实现在 netease_api.py 的签名函数

Layer 3: 自动刷新
├── HTTP 方式：auth_refresh.py (540行)
│   ├── preLogin → RSA 加密密码 → domainEntLogin → 处理 SMS 验证
│   └── 纯 HTTP 客户端，不依赖浏览器
├── 浏览器方式：browser_cookie.py (222行)
│   ├── Playwright 持久化浏览器
│   └── 支持 headless/headed 模式，等待手动登录
└── 401 响应自动触发 Cookie 刷新
```

### 1.4 速率限制

| 限制类型 | 值 | 实现方式 |
|----------|-----|----------|
| **全局 RPM** | 15 请求/分钟 | `flow_02` 中 `_netease_rate_limit()` 线程安全 deque |
| **搜索分页** | 每页最大结果数由 API 决定 | Flow 01 循环分页 |
| **401 重试** | 自动刷新 Cookie 后重试 | `netease_api.py` |

### 1.5 数据结构（返回值关键字段）

```python
# 公司搜索结果
{
    "company_name": str,
    "country": str,
    "website": str,
    "industry": str,
    # ... 更多字段
}

# 联系人数据
{
    "name": str,
    "email": str,
    "position": str,     # 用于 A/B/C/D 优先级分类
    "phone": str,
    # ... 更多字段
}
```

### 1.6 产品化影响

| 问题 | 严重度 | 说明 |
|------|--------|------|
| **Cookie 认证脆弱** | 🔴 高 | 非标准 OAuth/API Key，SMS 验证难自动化，多租户下每用户需独立 Cookie |
| **单一数据源** | 🟡 中 | 仅网易外贸通，产品化需支持 LinkedIn/Apollo/ZoomInfo 等 |
| **无官方 API 文档** | 🟡 中 | 接口可能随版本变更，缺乏稳定性保证 |
| **硬编码 PCB 行业** | 🟡 中 | 搜索参数和子行业列表硬编码，多行业需可配置化 |

---

## 2. OpenRouter（LLM 推理服务）

### 2.1 基本信息

| 项目 | 值 |
|------|-----|
| **服务提供商** | OpenRouter |
| **协议** | OpenAI 兼容 API |
| **API URL** | 环境变量 `LLM_API_URL` |
| **认证方式** | Bearer Token（API Key 存 DB `system_config` 表，key=`llm.openrouter_api_key`） |
| **代码位置** | `flows/utils/llm.py`（核心封装）, `api/routes_drafts.py`（内联调用） |

### 2.2 模型配置

| 用途 | 模型 ID | 定义位置 | 说明 |
|------|---------|----------|------|
| **公司评级**（主力） | `x-ai/grok-4.1-fast` | `config.py:56` | 高精度评级，支持联网搜索 |
| **邮件生成** | `deepseek/deepseek-chat` | `config.py:57` | 低成本高质量文本生成 |
| **评级降级 #1** | `perplexity/sonar` | `config.py:61` | 主力模型失败时的第一备选 |
| **评级降级 #2** | `deepseek/deepseek-chat` | `config.py:62` | 第二备选 |
| **草稿重写** | `deepseek/deepseek-chat` | `routes_drafts.py:80`（硬编码） | 用户手动触发的草稿修改 |

### 2.3 调用架构

```
call_llm_with_fallback()          # llm.py:126-158
├── 尝试 primary_model
│   └── call_llm()                # llm.py:44-123
│       ├── _get_api_key()        # 从 DB 读取 API Key
│       ├── POST {LLM_API_URL}/chat/completions
│       ├── 重试: 3次, backoff = attempt * 5s
│       └── 仅捕获 ConnectionError / Timeout
├── 响应为空或 JSON 解析失败 → 尝试 fallback_model_1
└── 继续失败 → 尝试 fallback_model_2
    └── 全部失败 → 返回空字符串 ""（不抛异常）
```

### 2.4 Prompt 策略

**公司评级 Prompt**（`flow_02:38-152`）：
- 多维度打分：相关性(40分) + 市场匹配(30分) + 意向度(30分) = 100分
- 评级规则：A级(≥70) / B级(40-69) / X级(<40)
- 指令 LLM 进行网络搜索，交叉验证 3+ 信息源
- 输出结构化 JSON：`score_details`, `company_profile`, `pcb_relevance`

**邮件生成 Prompt**（`email_templates.py:40-97`）：
- 注入联系人/公司上下文变量
- 要求生成个性化 B2B 冷邮件
- 输出 JSON：`{subject, body_target, body_zh}`（目标语言 + 中文对照）

**草稿重写**（`routes_drafts.py:57-73`）：
- 接收原始邮件正文 + 用户修改建议
- 返回重写后的纯文本（非 JSON）

### 2.5 JSON 解析策略

`parse_json_response()`：三轮容错解析
1. 直接 `json.loads()` 
2. 修复未转义换行符后重试
3. 正则提取 `{...}` 子串后解析

### 2.6 已知问题

| 问题 | 严重度 | 说明 |
|------|--------|------|
| **routes_drafts.py 内联调用** | 🟡 中 | 未复用 `llm.py` 封装，重复了 API Key 获取和请求逻辑 |
| **无 LLM 速率限制** | 🟡 中 | 仅靠 5 并发 worker 隐式限流，无显式 RPM 控制 |
| **失败静默返回空** | 🟡 中 | `call_llm()` 全部失败返回 `""`，上游需自行处理 |
| **模型名硬编码** | 🟡 中 | 模型在 config.py 配置但 routes_drafts.py 中硬编码 |
| **Prompt 绑定 PCB** | 🔴 高 | 评级和邮件 Prompt 内含 PCB/XAPCB 专用术语，多行业需模板化 |

### 2.7 产品化影响

| 改造项 | 说明 |
|--------|------|
| **Prompt 模板化** | 将行业知识、公司背景从 Prompt 中抽离为可配置参数 |
| **多租户 API Key** | 当前单一 Key 存 DB，需支持租户级别的 Key 管理或平台统一计费 |
| **模型选择策略** | 不同租户/套餐可配置不同模型（成本 vs 质量权衡） |
| **Token 用量追踪** | 需按租户追踪 token 消耗，用于计费 |
| **统一 LLM 入口** | 消除 routes_drafts.py 的内联调用，所有 LLM 调用走 llm.py |

---

## 3. EngageLab（邮件发送服务）

### 3.1 基本信息

| 项目 | 值 |
|------|-----|
| **服务提供商** | 极光（JiGuang）→ EngageLab |
| **API 端点** | `https://email.api.engagelab.cc/v1/` |
| **认证方式** | HTTP Basic Auth（`API_USER:CREDENTIAL`） |
| **代码位置** | `flows/utils/engagelab.py`（212行）, `api/routes_dashboard.py`（统计端点） |

### 3.2 API 使用

| API | HTTP | 路径 | 用途 | 调用者 |
|-----|------|------|------|--------|
| **发送邮件** | POST | `/v1/send` | 发送单封邮件 | Flow 04 |
| **每日统计** | GET | `/v1/stats_day` | 获取发送/打开/点击统计 | Dashboard API |
| **配额查询** | GET | （通过统计 API 推算） | 查询当日已用配额 | Dashboard API |

### 3.3 认证配置

**双源配置**（DB 优先，环境变量降级）：

```python
# 优先从 DB 读取
system_config 表:
  key='mail.engagelab_api_url'    → API 端点
  key='mail.engagelab_api_user'   → API 用户
  key='mail.engagelab_credential' → API 密钥
  key='mail.engagelab_sender'     → 发件人地址

# 降级到环境变量
ENGAGELAB_API_URL
ENGAGELAB_API_USER
ENGAGELAB_CREDENTIAL
ENGAGELAB_SENDER
```

### 3.4 发送流程

```
email_send_flow (Flow 04)
├── 1. 自动审批：>24h 未审批的草稿自动通过
├── 2. 时区过滤：仅在目标国家工作时间(9:00-17:00)发送
├── 3. 预热配额：20天升温计划 (5 → 2500 封/天)
│   └── 起始日期: 2026-02-25，按天数递增配额
├── 4. 逐封发送：
│   ├── send_email() → EngageLab POST /v1/send
│   ├── 内容格式：body_to_html() 自动段落化
│   ├── 3次重试（仅网络错误）
│   └── 更新 DB 状态 → 'sent' / 'send_failed'
└── 5. 每日汇总：发送统计报告邮件到配置的收件人
```

### 3.5 域名预热策略

```python
# config.py 中的预热计划（20天）
DOMAIN_WARMUP_PLAN = [
    5, 10, 20, 35, 50,           # Day 1-5
    75, 100, 150, 200, 300,      # Day 6-10
    400, 500, 700, 900, 1100,    # Day 11-15
    1300, 1600, 1900, 2200, 2500 # Day 16-20
]
WARMUP_START_DATE = "2026-02-25"
```

### 3.6 邮件内容处理

| 功能 | 实现 | 位置 |
|------|------|------|
| **HTML 转换** | `body_to_html()` — 纯文本自动段落化，保留换行 | `engagelab.py` |
| **纯文本版** | `body_to_text()` — 移除 HTML 标签 | `engagelab.py` |
| **问候检测** | 自动识别 "Dear/Hi/Hello" 开头 | `engagelab.py` |
| **签名分离** | 识别 "Best regards/Sincerely" 等签名标记 | `engagelab.py` |
| **邮箱验证** | `email_validator.py` — 正则 + DNS MX 记录查询 | 发送前校验 |

### 3.7 统计与追踪

Dashboard API 通过 EngageLab 的 `/v1/stats_day` 端点获取：

```python
# 可获取的指标
- 发送数 (sent_count)
- 送达数 (delivered_count)  
- 打开数 (open_count)
- 点击数 (click_count)
- 退订数 / 投诉数 / 硬弹数 / 软弹数
```

### 3.8 产品化影响

| 问题 | 严重度 | 说明 |
|------|--------|------|
| **单发件人** | 🔴 高 | 当前一个发件人地址，多租户需独立域名/发件人 |
| **预热硬编码** | 🟡 中 | 起始日期和计划写死在 config.py，需动态管理 |
| **无送达率监控** | 🟡 中 | 统计数据获取了但无自动告警（弹回率过高等） |
| **收件人列表管理** | 🟡 中 | 日报收件人硬编码 3 个邮箱，需可配置 |
| **单一发送通道** | 🟡 中 | 仅 EngageLab，无备用通道（如 SES/Mailgun） |

---

## 4. 环境变量汇总

### 4.1 完整变量清单

| 变量名 | 必需 | 用途 | 使用位置 |
|--------|------|------|----------|
| `FT_DB_HOST` | ✅ | PostgreSQL 主机 | `api/deps.py`, `flows/utils/db.py` |
| `FT_DB_PORT` | ❌ | PostgreSQL 端口（默认 5432） | 同上 |
| `FT_DB_USER` | ✅ | PostgreSQL 用户名 | 同上 |
| `FT_DB_NAME` | ✅ | PostgreSQL 数据库名 | 同上 |
| `PGPASSWORD` | ✅ | PostgreSQL 密码（API 层） | `api/deps.py` |
| `FT_DB_AUTH` | ✅ | PostgreSQL 密码（脚本层） | `scripts/export_*.py` |
| `LLM_API_URL` | ✅ | OpenRouter API 端点 | `flows/utils/llm.py`, `api/routes_drafts.py` |
| `ENGAGELAB_API_URL` | ❌* | EngageLab API 端点 | `flows/utils/engagelab.py` |
| `ENGAGELAB_API_USER` | ❌* | EngageLab API 用户 | 同上 |
| `ENGAGELAB_CREDENTIAL` | ❌* | EngageLab API 密钥 | 同上 |
| `ENGAGELAB_SENDER` | ❌* | 发件人邮箱 | 同上 |
| `VITE_API_BASE` | ❌ | 前端 API 地址 | `web/.env.development` |

> *标注 ❌* 的变量：DB `system_config` 表为主配置源，环境变量仅作降级

### 4.2 配置不一致问题

| 问题 | 说明 |
|------|------|
| **DB 密码双名** | API 层用 `PGPASSWORD`，脚本用 `FT_DB_AUTH`，应统一 |
| **无 .env.example** | 缺少环境变量模板文件，新部署靠口耳相传 |
| **DB vs ENV 双源** | EngageLab 和 LLM Key 同时支持 DB 和 ENV，增加排查复杂度 |

---

## 5. 集成依赖关系图

```
                         ┌──────────────┐
                         │   调度器      │
                         │ scheduler.py  │
                         └──────┬───────┘
                                │ 每30s触发
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Flow 01  │ │ Flow 02  │ │ Flow 04  │
              │关键词采集 │ │公司分析   │ │邮件发送   │
              └────┬─────┘ └──┬───┬───┘ └────┬─────┘
                   │          │   │          │
            ┌──────▼──────────▼───┘          │
            │                                │
     ┌──────▼───────┐  ┌──────────┐  ┌──────▼───────┐
     │ 网易外贸通    │  │OpenRouter │  │  EngageLab   │
     │              │  │          │  │              │
     │ • 公司搜索   │  │ • 评级   │  │ • 邮件发送   │
     │ • 联系人     │  │ • 写信   │  │ • 统计追踪   │
     │ • 详情/基本  │  │ • 重写   │  │              │
     └──────────────┘  └──────────┘  └──────────────┘
        Cookie+MD5      Bearer Token    Basic Auth
        15 RPM限流       5并发           预热配额
```

---

## 6. 产品化改造优先级

### P0 — 多租户化必须解决

| 改造项 | 涉及集成 | 工作量 |
|--------|----------|--------|
| 租户级别的网易账号/Cookie 管理 | 网易外贸通 | 大 |
| 租户级别的发件人/域名管理 | EngageLab | 大 |
| LLM API Key 租户隔离或平台统一计费 | OpenRouter | 中 |
| Token 用量按租户追踪 | OpenRouter | 中 |

### P1 — 产品质量提升

| 改造项 | 涉及集成 | 工作量 |
|--------|----------|--------|
| Prompt 模板化（去 PCB 硬编码） | OpenRouter | 中 |
| 域名预热动态管理 | EngageLab | 小 |
| 统一 LLM 调用入口 | OpenRouter | 小 |
| 环境变量规范化（.env.example + 统一命名） | 全部 | 小 |

### P2 — 扩展能力

| 改造项 | 涉及集成 | 工作量 |
|--------|----------|--------|
| 数据源插件架构（LinkedIn/Apollo/ZoomInfo） | 数据采集层 | 大 |
| 邮件通道备份（SES/Mailgun） | 邮件发送层 | 中 |
| 送达率监控与自动告警 | EngageLab | 中 |
| 模型选择策略（按租户/套餐配置） | OpenRouter | 中 |
