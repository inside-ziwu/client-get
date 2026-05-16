# 13 AI 集成方案

> **版本**: v1.0
> **日期**: 2026-04-17
> **输入文档**: `05_EXTERNAL_INTEGRATIONS.md`（§2 OpenRouter）, `07_REQUIREMENTS_SPEC.md`（场景⑥ + §2.4 余额耗尽 + 后台任务B/C）, `09_DATABASE_DESIGN.md`（§2.4 ai_models + §2.5 ai_usage_logs + §8.6 balance_transactions）, `10_API_DESIGN.md`（§7.3 评分服务内部端点）
> **目标读者**: AI Agent（解析 AI 集成架构）+ 后端工程师（实现 LLM 调用链路）

---

## 目录

1. [架构概述](#1-架构概述)
2. [OpenRouter 统一路由层](#2-openrouter-统一路由层)
3. [四种 AI 场景](#3-四种-ai-场景)
4. [计费与扣费机制](#4-计费与扣费机制)
5. [余额耗尽降级策略](#5-余额耗尽降级策略)
6. [Prompt 模板管理](#6-prompt-模板管理)
7. [模型降级与重试](#7-模型降级与重试)
8. [Token 计数与成本计算](#8-token-计数与成本计算)
9. [可观测性](#9-可观测性)

---

## 1. 架构概述

### 1.1 核心决策

| 决策 | 选择 | 原因 |
|------|------|------|
| LLM 路由 | OpenRouter 统一路由 | 单一 API Key，切换模型仅改 model_id |
| API Key 管理 | 平台级统一，租户无感 | 运营集中管理，避免租户泄露 Key |
| 计费单位 | 人民币（token → 元换算） | 面向中国客户 |
| 余额控制 | 原子条件更新（见 `09_DATABASE_DESIGN.md` §8.6） | 无锁高性能 |

### 1.2 调用链路

```
租户操作 / 后台任务
       │
       ▼
  ┌──────────────┐     余额检查
  │  AI Service  │ ◄── (原子扣费)
  │  Layer       │
  └──────┬───────┘
         │ 选择模型 (ai_models 表)
         ▼
  ┌──────────────┐
  │ OpenRouter   │ ←── 单一 API Key（平台级）
  │ Client       │
  └──────┬───────┘
         │ POST /chat/completions
         ▼
  ┌──────────────┐
  │ OpenRouter   │ → 路由到具体模型
  │ Service      │   (GPT-4o / DeepSeek / Gemini / etc.)
  └──────┬───────┘
         │ 响应 (含 usage.prompt_tokens / completion_tokens)
         ▼
  ┌──────────────┐
  │ 计费记录     │ → ai_usage_logs + balance_transactions
  └──────────────┘
```

---

## 2. OpenRouter 统一路由层

### 2.1 客户端封装

继承并改造现有 `flows/utils/llm.py`，增加多租户计费能力：

```python
from dataclasses import dataclass

@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float

class OpenRouterClient:
    """OpenRouter 统一客户端"""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=60)

    async def chat_completion(
        self,
        model_id: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """
        调用 OpenRouter chat/completions（OpenAI 兼容协议）
        """
        start = time.monotonic()
        resp = await self.client.post(
            f"{self.api_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": messages,
                "temperature": temperature,
                **({"max_tokens": max_tokens} if max_tokens else {}),
                **({"response_format": response_format} if response_format else {}),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        elapsed = (time.monotonic() - start) * 1000

        usage = data.get("usage", {})
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", model_id),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            latency_ms=elapsed,
        )
```

### 2.2 模型注册

模型在 `ai_models` 表中注册（见 `09_DATABASE_DESIGN.md` §2.4）：

| 字段 | 说明 |
|------|------|
| `model_id` | OpenRouter 模型标识（如 `x-ai/grok-4.1-fast`） |
| `model_type` | 用途分类：`scoring` / `email_generation` / `intelligence_summary` / `data_analysis` |
| `input_price` | 每 1K input token 人民币单价 |
| `output_price` | 每 1K output token 人民币单价 |
| `is_active` | 是否可用 |

平台运营在管理后台配置模型及单价（见 `07_REQUIREMENTS_SPEC.md` 场景⑥）。

---

## 3. 四种 AI 场景

### 3.1 场景一览

| 场景 | 触发方式 | 模型类型 | 费用归属 | 频率 |
|------|---------|---------|---------|------|
| 评分 LLM 辅助 | 后台任务 C（T+1） | `scoring` | 被评分公司关联的租户 | 高频 |
| 邮件 AI 生成 | 用户触发 | `email_generation` | 触发租户 | 中频 |
| 情报 AI 摘要 | 后台任务 B（每日） | `intelligence_summary` | 均摊给同行业所有租户 | 低频 |
| AI 数据分析 | 用户触发 | `data_analysis` | 触发租户 | 低频 |

### 3.2 评分 LLM 辅助

> 对应现有 Flow 02 company_analysis 的 LLM 评分部分。

**改造要点**：

| 现有 | 新系统 |
|------|--------|
| 固定 A/B/X 三级 | JSONB 规则引擎 + S/A/B/C/D 五级 |
| 硬编码 16 类 PCB 行业 | 租户自定义 `scoring_templates` |
| 全量 LLM 评分 | 仅 `type='llm'` 的维度调用 LLM |
| 无计费 | 按实际 token 消耗扣费 |

**流程**：

```python
async def score_company_with_llm(
    tenant_id: UUID,
    company: SharedCompany,
    llm_dimensions: list[dict],  # scoring_template 中 type='llm' 的维度
    model: AIModel,
) -> dict[str, int]:
    """
    对公司执行 LLM 辅助评分维度。
    每个 LLM 维度单独调用（或合并为一个 prompt）。
    """
    # 1. 余额预检
    estimated_cost = estimate_cost(model, estimated_tokens=2000)
    if not await check_balance(tenant_id, estimated_cost):
        raise InsufficientBalanceError(tenant_id)

    # 2. 构建 Prompt
    messages = build_scoring_prompt(company, llm_dimensions)

    # 3. 调用 LLM
    response = await openrouter_client.chat_completion(
        model_id=model.openrouter_model_id,
        messages=messages,
        temperature=0.3,  # 评分需要确定性
        response_format={"type": "json_object"},
    )

    # 4. 计费（原子扣费，见 §4）
    await record_and_charge(
        tenant_id=tenant_id,
        model=model,
        response=response,
        usage_type="scoring",
        entity_type="company",
        entity_id=company.id,
    )

    # 5. 解析结果
    return parse_scoring_result(response.content, llm_dimensions)
```

**评分维度执行顺序**：

```
scoring_template.rules.dimensions
  ├── type='rule' 维度 → 纯规则计算（不消耗 AI 余额）
  └── type='llm' 维度 → 调用 LLM（消耗 AI 余额）
```

纯规则维度始终执行；LLM 维度在余额不足时跳过，业务状态统一仍显示为 `pending_score`，技术标记写入 `company_scores.llm_pending = true`。

### 3.3 邮件 AI 生成

> 对应现有 Flow 03 email_draft。

用户在发送计划中为序列步骤生成邮件内容：

```python
async def generate_email(
    tenant_id: UUID,
    user_id: UUID,
    template: EmailTemplate,
    company: TenantCompany,
    contact: TenantContact,
    model: AIModel,
) -> GeneratedEmail:
    # 1. 余额预检
    if not await check_balance(tenant_id, estimate_cost(model, 3000)):
        raise InsufficientBalanceError(tenant_id)

    # 2. 构建 Prompt（模板变量 + 公司/联系人上下文）
    messages = build_email_prompt(template, company, contact)

    # 3. 调用 LLM（生成 2-3 个版本）
    versions = []
    for i in range(3):
        resp = await openrouter_client.chat_completion(
            model_id=model.openrouter_model_id,
            messages=messages,
            temperature=0.8 + i * 0.05,  # 微调温度产生差异
        )
        versions.append(resp)
        await record_and_charge(
            tenant_id=tenant_id, user_id=user_id,
            model=model, response=resp,
            usage_type="email_generation",
            entity_type="email", entity_id=None,
        )

    return GeneratedEmail(versions=[v.content for v in versions])
```

### 3.4 情报 AI 摘要

> 对应后台任务 B。费用均摊给同行业所有租户。

```python
async def summarize_article(
    article: IntelligenceArticle,
    subscribing_tenant_ids: list[UUID],
    model: AIModel,
) -> str:
    """
    AI 摘要一篇情报文章。
    费用均摊给所有订阅该行业的租户。
    """
    resp = await openrouter_client.chat_completion(
        model_id=model.openrouter_model_id,
        messages=build_summary_prompt(article),
        temperature=0.5,
    )

    # 均摊计费
    total_cost = calculate_cost(model, resp)
    per_tenant_cost = total_cost / len(subscribing_tenant_ids)

    for tid in subscribing_tenant_ids:
        success = await atomic_charge(tid, per_tenant_cost)
        if not success:
            # 余额不足的租户：不展示 AI 摘要（仅标题+链接）
            logger.info(f"Tenant {tid} insufficient balance for intelligence summary")

        await insert_usage_log(
            tenant_id=tid, model=model, response=resp,
            usage_type="intelligence_summary",
            entity_type="article", entity_id=article.id,
            cost=per_tenant_cost,
        )

    return resp.content
```

### 3.5 AI 数据分析

用户在邮件监控页面触发，分析发送效果并生成优化建议：

```python
async def analyze_sending_performance(
    tenant_id: UUID,
    user_id: UUID,
    plan_id: UUID,
    model: AIModel,
) -> AnalysisResult:
    # 1. 聚合数据
    stats = await get_plan_statistics(plan_id)

    # 2. 构建 Prompt
    messages = build_analysis_prompt(stats)

    # 3. 调用 LLM
    resp = await openrouter_client.chat_completion(
        model_id=model.openrouter_model_id,
        messages=messages,
        temperature=0.5,
    )

    # 4. 计费（触发租户付费）
    await record_and_charge(
        tenant_id=tenant_id, user_id=user_id,
        model=model, response=resp,
        usage_type="other",
        entity_type="plan", entity_id=plan_id,
    )

    return parse_analysis(resp.content)
```

---

## 4. 计费与扣费机制

### 4.1 扣费流程

每次 LLM 调用分为两步：先预授权，再按真实 token 结算差额并记录 usage：

```python
async def settle_ai_usage(
    tenant_id: UUID,
    model: AIModel,
    response: LLMResponse,
    usage_type: str,
    entity_type: str,
    entity_id: UUID | None,
    authorization_txn_id: UUID,
    estimated_cost: Decimal,
    user_id: UUID | None = None,
):
    """结算 AI 使用：补扣或释放差额，并记录 ai_usage_logs"""
    actual_cost = calculate_cost(model, response)
    delta = actual_cost - estimated_cost

    async with db.transaction() as conn:
        # 1. 补扣或释放预授权差额
        if delta > 0:
            await conn.execute("SELECT charge_reserved_delta($1, $2)", authorization_txn_id, delta)
        elif delta < 0:
            await conn.execute("SELECT release_reserved_delta($1, $2)", authorization_txn_id, -delta)

        # 2. INSERT ai_usage_logs
        await conn.execute("""
            INSERT INTO ai_usage_logs
                (id, tenant_id, user_id, model_id, usage_type,
                 entity_type, entity_id,
                 input_tokens, output_tokens, total_tokens,
                 cost, balance_transaction_id, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
        """, gen_uuid_v7(), tenant_id, user_id, model.id, usage_type,
            entity_type, entity_id,
            response.input_tokens, response.output_tokens, response.total_tokens,
            actual_cost, authorization_txn_id)
```

### 4.1.1 结算差额状态机

为避免“供应商成功但本地落账失败”或“本地预扣后供应商超时”的灰区，统一采用以下状态机：

| 阶段 | 触发条件 | 余额动作 | 流水建议 |
|------|---------|---------|---------|
| `authorized` | 调用前预算校验通过 | 先冻结/预扣估算金额 | `balance_transactions.type='consumption'`，`reference_type='ai_authorization_hold'` |
| `settled_exact` | `actual_cost = estimated_cost` | 不再额外变动 | 复用预授权流水 |
| `settled_charge` | `actual_cost > estimated_cost` | 再补扣差额 | 新增 `consumption` 流水，`reference_type='ai_settlement_delta'` |
| `settled_release` | `actual_cost < estimated_cost` | 退回差额 | 新增 `refund` 流水，`reference_type='ai_settlement_release'` |
| `released_full` | 调用失败且无有效输出 | 退回全部预授权 | 新增 `refund` 流水，`reference_type='ai_authorization_release'` |

**失败分支约束**：
1. Provider 超时、5xx、网络错误且未拿到可计费响应时，必须释放全部预授权。
2. 若已拿到供应商响应但本地结算失败，必须以 `authorization_txn_id` 作为幂等键重试结算，禁止再次调用模型。
3. `ai_usage_logs` 只在成功拿到可计费响应后写入；纯释放场景不写 usage log，只写释放流水。
4. 情报摘要均摊场景需要先为每个分摊租户各自做预授权，再按各自差额结算，不允许先成功写摘要、后批量尝试扣费。

### 4.2 费用归属规则

| 场景 | 归属规则 | 实现 |
|------|---------|------|
| 评分 LLM 辅助 | 被评分公司关联的租户 | `tenant_companies.tenant_id` |
| 邮件 AI 生成 | 触发操作的租户 | 请求上下文中的 `tenant_id` |
| 情报 AI 摘要 | 均摊给同行业所有租户 | `intelligence_subscriptions` 查询订阅租户 |
| AI 数据分析 | 触发操作的租户 | 请求上下文中的 `tenant_id` |

### 4.3 先扣费再调用 vs 先调用再扣费

**选择：预授权 + 调用后精确结算**。

| 方案 | 优势 | 劣势 |
|------|------|------|
| 预授权 + 结算差额 | 不透支，且最终按真实 token 计费 | 需要两笔账务动作（预留 / 结算） |
| 先调用再扣费 | 实现简单 | 成功调用后可能无法落账，审计不一致 |

**理由**：多租户 SaaS 首发必须优先保证账务一致性。先做预授权，调用成功后再按真实 token 补扣或释放差额，避免“调用成功但扣费失败”。

```python
async def authorize_ai_budget(tenant_id: UUID, estimated_cost: Decimal) -> UUID:
    """预留本次 AI 调用预算，返回预授权流水 ID"""
    txn_id = gen_uuid_v7()
    async with db.transaction() as conn:
        result = await conn.fetchrow("""
            UPDATE tenants
            SET balance = balance - $1, updated_at = NOW()
            WHERE id = $2 AND balance >= $1
            RETURNING balance
        """, estimated_cost, tenant_id)
        if result is None:
            raise InsufficientBalanceError(tenant_id)
        await conn.execute("""
            INSERT INTO balance_transactions
              (id, tenant_id, type, amount, balance_before, balance_after, reference_type, description, created_at)
            VALUES ($1, $2, 'consumption', $3, $4, $5, 'ai_authorization_hold', 'AI预授权占用', NOW())
        """, txn_id, tenant_id, -estimated_cost, result["balance"] + estimated_cost, result["balance"])
    return txn_id
```

### 4.3.1 失败补偿伪代码

```python
async def finalize_or_release_authorization(
    authorization_txn_id: UUID,
    tenant_id: UUID,
    provider_response: LLMResponse | None,
    model: AIModel,
    usage_context: dict,
):
    """统一处理调用完成后的补扣 / 退回 / 全额释放"""
    if provider_response is None:
        await release_full_authorization(
            authorization_txn_id,
            tenant_id,
            reference_type="ai_authorization_release",
        )
        return

    # 已拿到响应，必须走幂等结算，不允许重新调用模型
    await settle_ai_usage(
        tenant_id=tenant_id,
        model=model,
        response=provider_response,
        authorization_txn_id=authorization_txn_id,
        **usage_context,
    )
```

---

## 5. 余额耗尽降级策略

> 见 `07_REQUIREMENTS_SPEC.md` §2.4。

| 功能 | 余额为 0 时行为 | 实现方式 |
|------|----------------|---------|
| 评分（LLM 辅助维度） | 暂停该租户全部 LLM 评分，新公司业务状态仍为 `pending_score` | 预授权失败 → 跳过 LLM 维度，纯规则维度照常，并写 `llm_pending=true` |
| 情报 AI 摘要 | 仅展示标题和链接，无 AI 摘要 | 均摊扣费失败 → `article_publications.has_summary = false` |
| 邮件 AI 生成 | "AI 生成"按钮置灰 | 前端读取 `GET /ai-capabilities` → 按钮 disabled + tooltip |
| AI 数据分析 | "AI 分析"按钮置灰 | 同上 |
| 纯规则评分 | **不受影响** | 不走 LLM，不扣余额 |
| 邮件发送 / 数据浏览 | **不受影响** | 不消耗 AI 余额 |

### 5.1 前端能力状态

由于 `07_REQUIREMENTS_SPEC.md` 规定 AI 余额仅管理员可查看，Operator/Viewer 不直接读取余额数值。Tenant API 需要通过 `GET /t/{slug}/api/v1/ai-capabilities` 提供“当前用户是否可用该 AI 功能”的能力态，而不是把余额端点开放给所有角色：

```typescript
interface AIFeatureCapability {
  feature: "email_generate" | "email_analysis" | "intelligence_summary";
  available: boolean;
  reason?: "insufficient_balance" | "role_denied" | "model_unavailable";
}

// 前端根据 available 控制按钮状态
const canGenerateEmail = capability.available;
```

推荐来源：
- 管理员：可调用 `GET /billing/balance` 查看余额，同时读取 capability。
- 业务员：仅读取 capability，不暴露具体余额金额。

### 5.2 充值后补评

余额不足期间积压的 `llm_pending=true` 公司，充值后需要补评：

```python
async def trigger_pending_scoring(tenant_id: UUID):
    """充值成功后，触发积压的 LLM 评分"""
    pending_companies = await db.fetch_all("""
        SELECT tc.id FROM tenant_companies tc
        JOIN company_scores cs ON cs.tenant_company_id = tc.id
        WHERE tc.tenant_id = $1 AND cs.llm_pending = true
    """, tenant_id)

    if pending_companies:
        await internal_client.post("/scoring/trigger", json={
            "tenant_id": str(tenant_id),
            "company_ids": [str(c["id"]) for c in pending_companies],
        })
```

---

## 6. Prompt 模板管理

### 6.1 模板存储

Prompt 模板按场景存储，支持版本管理：

| 场景 | 存储位置 | 可编辑性 |
|------|---------|---------|
| 评分 LLM 维度 | `scoring_template_versions.rules.dimensions[].prompt_template` | 租户可编辑（通过评分规则配置） |
| 邮件生成 | `platform_email_templates` + `email_templates` | 平台模板 + 租户自定义 |
| 情报摘要 | 代码内置（Phase 1） | 后续可迁移到 DB |
| 数据分析 | 代码内置（Phase 1） | 后续可迁移到 DB |

### 6.2 变量替换

```python
PROMPT_VARIABLES = {
    # 公司上下文
    "{company_name}": lambda ctx: ctx.company.name,
    "{country}": lambda ctx: ctx.company.country,
    "{industry}": lambda ctx: ctx.company.industry,
    "{website}": lambda ctx: ctx.company.website,
    # 联系人上下文
    "{contact_name}": lambda ctx: ctx.contact.name if ctx.contact else "",
    "{contact_title}": lambda ctx: ctx.contact.title if ctx.contact else "",
    # 租户上下文
    "{tenant_industry}": lambda ctx: ctx.tenant.industry,
    "{tenant_products}": lambda ctx: ", ".join(ctx.tenant.product_tags),
}

def render_prompt(template: str, context: PromptContext) -> str:
    result = template
    for var, resolver in PROMPT_VARIABLES.items():
        result = result.replace(var, str(resolver(context) or ""))
    return result
```

### 6.3 评分 Prompt 示例

```
你是一位专业的B2B销售分析师。请评估以下公司与{tenant_industry}行业的匹配度。

公司信息：
- 名称：{company_name}
- 国家：{country}
- 行业：{industry}
- 网站：{website}

请从以下维度评分（0-100）：
{llm_dimensions_description}

返回JSON格式：
{
  "dimension_id_1": {"score": 85, "reasoning": "..."},
  "dimension_id_2": {"score": 60, "reasoning": "..."}
}
```

---

## 7. 模型降级与重试

### 7.1 降级链

继承现有 `call_llm_with_fallback()` 模式，按场景配置降级链：

```python
MODEL_FALLBACK_CHAINS: dict[str, list[str]] = {
    "scoring": [
        "x-ai/grok-4.1-fast",        # 主力（高精度，支持联网）
        "perplexity/sonar",           # 降级 1
        "deepseek/deepseek-chat",     # 降级 2
    ],
    "email_generation": [
        "deepseek/deepseek-chat",     # 主力（低成本高质量）
        "google/gemini-2.5-flash",    # 降级
    ],
    "intelligence_summary": [
        "deepseek/deepseek-chat",
        "google/gemini-2.5-flash",
    ],
}
```

### 7.2 降级触发条件

| 条件 | 行为 |
|------|------|
| HTTP 5xx | 重试当前模型（最多 3 次，指数退避） |
| HTTP 429 (Rate Limit) | 等待后重试（尊重 Retry-After header） |
| 响应为空 / JSON 解析失败 | 切换到降级模型 |
| 连续 3 次失败 | 切换到下一个降级模型 |
| 所有模型都失败 | 返回空结果，记录告警 |

### 7.3 重试实现

```python
async def call_with_fallback(
    usage_type: str,
    messages: list[dict],
    **kwargs,
) -> LLMResponse | None:
    chain = MODEL_FALLBACK_CHAINS.get(usage_type, [])

    for model_id in chain:
        for attempt in range(3):
            try:
                return await openrouter_client.chat_completion(
                    model_id=model_id,
                    messages=messages,
                    **kwargs,
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", "5"))
                    await asyncio.sleep(retry_after)
                elif e.response.status_code >= 500:
                    await asyncio.sleep(3 * (attempt + 1))
                else:
                    break  # 4xx 非 429，不重试
            except (httpx.ConnectError, httpx.ReadTimeout):
                await asyncio.sleep(3 * (attempt + 1))

        logger.warning(f"Model {model_id} failed after retries, trying next")

    logger.error(f"All models failed for {usage_type}")
    return None
```

---

## 8. Token 计数与成本计算

### 8.1 Token 来源

OpenRouter 响应中包含 `usage` 字段：

```json
{
  "usage": {
    "prompt_tokens": 1234,
    "completion_tokens": 567,
    "total_tokens": 1801
  }
}
```

直接使用 API 返回的 token 数，不自行计算（避免 tokenizer 差异）。

### 8.2 成本计算

```python
def calculate_cost(model: AIModel, response: LLMResponse) -> Decimal:
    """
    计算人民币费用。
    model.input_price / output_price 单位：元/1K token
    """
    input_cost = Decimal(response.input_tokens) / 1000 * model.input_price
    output_cost = Decimal(response.output_tokens) / 1000 * model.output_price
    return (input_cost + output_cost).quantize(Decimal("0.0001"))
```

### 8.3 预估函数

用于余额预检（§4.3）：

```python
ESTIMATED_TOKENS: dict[str, int] = {
    "scoring": 2000,              # 输入~1500 + 输出~500
    "email_generation": 3000,     # 输入~1000 + 输出~2000
    "intelligence_summary": 4000, # 输入~3000 + 输出~1000
    "data_analysis": 5000,        # 输入~3500 + 输出~1500
}

def estimate_cost(model: AIModel, usage_type: str) -> Decimal:
    tokens = ESTIMATED_TOKENS.get(usage_type, 3000)
    # 粗略按 input:output = 2:1 估算
    input_tokens = tokens * 2 // 3
    output_tokens = tokens // 3
    return (
        Decimal(input_tokens) / 1000 * model.input_price
        + Decimal(output_tokens) / 1000 * model.output_price
    ).quantize(Decimal("0.0001"))
```

---

## 9. 可观测性

### 9.1 关键指标

| 指标 | 类型 | 告警阈值 |
|------|------|---------|
| `ai.calls.total` | Counter (by usage_type, model) | - |
| `ai.calls.failures` | Counter (by usage_type, model) | > 10/min |
| `ai.calls.latency_ms` | Histogram | P99 > 10000ms |
| `ai.tokens.input` | Counter (by model) | - |
| `ai.tokens.output` | Counter (by model) | - |
| `ai.cost.total_rmb` | Counter (by tenant, usage_type) | - |
| `ai.balance.low` | Gauge (per tenant) | balance < threshold |
| `ai.fallback.triggered` | Counter (by usage_type) | > 5/hour |

### 9.2 日志规范

```python
logger.info("llm_call_completed",
    extra={
        "tenant_id": str(tenant_id),
        "usage_type": usage_type,
        "model": model.openrouter_model_id,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "cost_rmb": str(cost),
        "latency_ms": response.latency_ms,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
    })
```

### 9.3 管理后台统计

平台运营可在管理后台查看：

| 统计项 | 数据来源 |
|--------|---------|
| 各租户 AI 消费排行 | `ai_usage_logs` GROUP BY tenant_id |
| 各模型调用量 / 成本 | `ai_usage_logs` GROUP BY model_id |
| 各场景 token 消耗趋势 | `ai_usage_logs` GROUP BY usage_type, DATE(created_at) |
| 余额不足事件 | 应用日志 + `notifications` |

---

> **文档结束**
> 下一步：`11_FRONTEND_ARCHITECTURE.md`（前端架构设计，需先读取 `04_FRONTEND_MAP.md` + `08_UI_SPEC.md`）
