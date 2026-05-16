# 调研：sysdev-ft-marketing 邮件发送机制

## 结论

邮件通过 **EngageLab API** 发送，采用 **Prefect 工作流 + 计划驱动调度器** 的架构，支持域名预热和时区感知发送。

---

## 邮件发送完整流程

### 1. 触发机制

**调度器** (`scripts/scheduler.py`) 每 **30 秒**扫描一次活跃计划：

```
扫描 email_plans (status NOT IN draft/done)
  → 检查是否有 approved 状态的草稿
  → 派发 flow_04_email_send (在独立线程中执行)
```

### 2. 审批门控

草稿必须满足以下条件之一才能发送：

| 条件 | 说明 |
|------|------|
| `send_status = 'approved'` | 单独审批的草稿 |
| `send_status = 'draft'` + 关联 plan `approval_status = 'approved'` | 所属计划已审批 |
| `created_at < NOW() - 24h` | 超过 24 小时自动审批 |

**第二/第三封邮件** (`scripts/followup_auto_sender.py`)：轮询监控，每 30 秒检查第二/第三轮草稿，自动审批后触发发送。

### 3. 发送流程 (`flows/flow_04_email_send.py`)

```python
email_send_flow(batch_size, plan_id)
```

**步骤：**
1. **自动审批** — 将超过 24 小时的 draft 草稿置为 approved
2. **预热额度检查** — 计算今日剩余可发送数量
3. **时区过滤** — 扫描可发送国家池（仅工作日 9:00-17:00 的国家）
4. **查询待发送草稿** — 按国家过滤已审批草稿
5. **逐封发送** — 调用 EngageLab API
6. **回写状态** — 成功标记 `sent`，失败标记 `failed`
7. **每日定投** — 向监控邮箱发送随机草稿

### 4. EngageLab API 调用 (`flows/utils/engagelab.py`)

```python
send_email(to, subject, html_body, text_body)
```

**请求格式：**
```json
{
  "from": "sender@example.com",
  "to": ["recipient@example.com"],
  "body": {
    "subject": "邮件主题",
    "content": {
      "html": "<div>...</div>",
      "text": "纯文本内容"
    },
    "settings": {
      "send_mode": 0,
      "return_email_id": true,
      "open_tracking": true,
      "click_tracking": false,
      "unsubscribe_tracking": false
    }
  }
}
```

**认证方式：** Basic Auth（`user:credential` Base64 编码）

**配置来源（优先级）：**
1. 数据库 `system_config` 表（`mail.engagelab_*` 键）
2. 环境变量（`ENGAGELAB_API_USER`, `ENGAGELAB_CREDENTIAL`, `ENGAGELAB_SENDER`, `ENGAGELAB_API_URL`）

### 5. 域名预热机制 (`flows/utils/warmup.py`)

从 2026-02-25 开始的 20 天预热计划：

| 天数 | 每日上限 |
|------|----------|
| Day 1 | 5 |
| Day 5 | 50 |
| Day 10 | 200 |
| Day 15 | 1000 |
| Day 20+ | 2500 |

**额度计算：**
- `get_remaining_quota()` = 全局每日上限 - 今日已发送
- `get_plan_daily_limit()` = 预热计划对应天数的上限
- 实际发送目标 = `min(remaining, plan_daily_limit)`

### 6. 时区感知发送

- 维护 `COUNTRY_TIMEZONE` 映射（40+ 国家）
- 仅在目标国家的 **工作日 9:00-17:00** 发送
- 系统时区：`Asia/Shanghai`

### 7. 邮件内容生成 (`flows/flow_03_email_draft.py`)

- LLM 生成个性化开发信（DeepSeek 模板驱动）
- 支持多语言（根据国家自动识别）
- 签名自动附加（Kevin Zhao / XAPCB）
- 存入 `email_drafts` 表，状态 `draft`

---

## 关键文件

| 文件 | 职责 |
|------|------|
| `flows/flow_04_email_send.py` | 邮件发送主流程 |
| `flows/flow_03_email_draft.py` | 邮件草稿生成 |
| `flows/utils/engagelab.py` | EngageLab API 封装 |
| `flows/utils/warmup.py` | 域名预热额度计算 |
| `flows/config.py` | 常量配置（时区、预热计划等） |
| `scripts/scheduler.py` | 计划驱动调度器 |
| `scripts/followup_auto_sender.py` | 跟进邮件自动发送 |

---

## 数据流

```
email_drafts (send_status=draft)
  → [审批/超时自动审批]
  → email_drafts (send_status=approved)
  → [调度器扫描 + 时区过滤]
  → EngageLab API
  → email_drafts (send_status=sent/failed)
```
