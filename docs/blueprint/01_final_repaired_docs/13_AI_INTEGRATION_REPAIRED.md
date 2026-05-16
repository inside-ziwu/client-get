# 13 AI 集成方案（修复版）

## 1. 总体原则

- OpenRouter 平台级统一 API Key。
- 租户不管理 Key，只管理人民币 AI 余额。
- 所有 AI 调用必须经过 AI Service，禁止路由层直接调 OpenRouter。
- 所有成功可计费调用必须写 `ai_usage_logs` 与 `balance_transactions`。

## 2. AI 场景

| usage_type | 场景 | 费用归属 | 前端能力 |
|---|---|---|---|
| `scoring` | LLM 辅助评分 | 被评分公司所属租户 | 不展示按钮，后台任务。 |
| `email_generation` | 邮件模板/个性化生成 | 操作租户 | `email_generate`。 |
| `intelligence_summary` | 情报摘要 | 同行业订阅租户均摊 | `intelligence_summary`。 |
| `data_analysis` | 邮件效果 AI 分析 | 操作租户 | `email_analysis`。 |

## 3. 模型配置

`ai_models.model_type` 使用：

```text
scoring / email_generation / intelligence_summary / data_analysis / general
```

`ai_scene_defaults.scene` 使用同一组 scene。

## 4. 预授权与结算状态机

### 4.1 状态

```text
authorized
settled_exact
settled_charge
settled_release
released_full
settlement_failed
```

### 4.2 成功路径

1. 估算 token 与费用。
2. `authorize_ai_budget(tenant_id, estimated_cost)`：原子扣减余额，插入 hold 流水。
3. 调 OpenRouter。
4. 根据 provider usage 计算 actual_cost。
5. `settle_ai_usage()`：补扣或释放差额，更新 AI attempt log 与结算流水。
6. 返回结果。

### 4.3 失败路径

- 调用失败且无有效输出：释放全部 hold，AI attempt log 标记为 `released_full`、`actual_cost=0`；不计入可计费用量。
- 已拿到 provider 响应但本地落账失败：记录 `settlement_failed`，后台以 `authorization_transaction_id` 幂等重试结算，不允许重复调用模型。

## 5. 情报摘要均摊

正确顺序：

1. 找到订阅该行业的 active tenants。
2. 每个 tenant 分别预授权估算份额。
3. 只对预授权成功的租户计入分摊对象。
4. 调用一次 LLM。
5. 对成功预授权的租户分别结算。
6. 发布时，余额不足租户 `has_summary=false`。

不要先生成摘要再批量扣费。

## 6. 余额耗尽降级

| 功能 | 后端行为 |
|---|---|
| 评分 LLM 维度 | 写 pending，不阻塞纯规则评分。 |
| 情报摘要 | 只发布标题/链接。 |
| 邮件 AI 生成 | `/ai-capabilities` 返回 unavailable。 |
| AI 数据分析 | `/ai-capabilities` 返回 unavailable。 |
| 邮件发送 | 不受影响。 |

## 7. Prompt 管理

- 评分 prompt 来自 scoring_template dimension。
- 邮件生成 prompt 来自平台/租户模板 + 用户输入。
- 情报摘要与数据分析 Phase 1 可代码内置，但必须以 service 层常量集中管理。
- 所有 prompt 变量必须经过白名单替换，不允许把用户输入当 Jinja 代码执行。

## 8. 可观测性

记录：

- scene / model / tenant / user / entity。
- provider_request_id。
- latency_ms。
- input/output/total tokens。
- estimated/actual cost。
- settlement_status。
- error_code/error_message。
