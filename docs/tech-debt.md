# 技术债 / 待改进清单

> **用途**:记录已发现但未即时修复的系统缺陷、功能缺口、技术债。新项往下追加,编号递增(TD-N),不复用旧号。
> **约定**:每项标注状态、发现日期、来源;真正动手修复时走当前工作流(`ce-brainstorm` →〔视复杂度〕`ce-plan` → `writing-plans` → 实施),不直接改代码。
> **状态图例**:🔴 未开始 ｜ 🟡 进行中 ｜ ✅ 已解决(解决后保留条目并标注 commit / PR)

## 索引

| # | 待改进项 | 性质 | 状态 |
|---|---|---|---|
| [TD-1](#td-1--域名验证是假验证) | 域名「验证」是假验证 | UX 缺陷 / 误导 | 🔴 |
| [TD-2](#td-2--预热域名不会自动升档) | 预热域名不会自动升档 | 功能缺口 | 🔴 |
| [TD-3](#td-3--ai-无真实推理当前为启发式桩) | AI 无真实推理(当前为桩) | 核心功能未实现 | 🔴 |
| [TD-4](#td-4--数据源腾道命名分裂-tendata--tengdao) | 数据源腾道命名分裂 | 数据一致性隐患 | 🔴 |

> TD-1~TD-4 均于 **2026-07-06 整理 B 实例运营手册时**发现(5 路子系统代码排查 + 生产库核对)。参见 [docs/handovers/2026-07-06-b-instance-operations-manual.md](handovers/2026-07-06-b-instance-operations-manual.md)。

---

## TD-1 · 域名「验证」是假验证

- **状态**:🔴 未开始
- **性质**:UX 缺陷 / 误导
- **发现**:2026-07-06

**问题**:admin 后台租户详情页「域名」标签的「验证」按钮,后端 `verify_tenant_domain`（`backend/app/services/admin_config_service.py:1707-1752`)**无条件**把 `domain_warmup_status.verification_status` 置为 `verified`、写 `dns_verified_at=now()`,**不做任何真实 DNS / SPF / DKIM / DMARC 校验,也不调用 EngageLab**。EngageLab 集成(`backend/app/integrations/engagelab.py`)只有 `send_email`、`query_email_status` 两个方法,无域名验证 API。

**后果**:运营点了「验证」以为域名可发信,实际必须先在 EngageLab 后台完成该域名 DNS 认证,否则发送失败。误导性强。

**建议方向**(二选一,需产品决策):
1. 做真实校验:后端实际查询 DNS TXT(SPF/DKIM/DMARC)后再置 verified,或调用 EngageLab 域名状态接口(若有)。
2. 短期不做真验证:UI 明确改文案,提示「验证仅为内部标记,发信前必须先在 EngageLab 完成 DNS 认证」。

**入口**:前端 `frontend/apps/admin/src/app/(dashboard)/tenants/client-page.tsx` 域名标签。

---

## TD-2 · 预热域名不会自动升档

- **状态**:🔴 未开始
- **性质**:功能缺口
- **发现**:2026-07-06

**问题**:域名预热**不会自动升档**。`warmup_rule_levels` 表定义了升档条件字段(`min_stay_days`、`min_delivery_rate`、`max_bounce_rate`、`max_complaint_rate`),`warmup_rules.min_observation_emails` 也在,但全代码库**没有任何 worker / 定时任务据此自动提升 `domain_warmup_status.warmup_level`**——这些阈值字段只被写入 / 展示,从不被读来做判断。`domain_warmup_history.change_type` 的 CHECK 允许 `level_up`/`level_down`,但代码实际只写 `manual_adjust`(`admin_config_service.py` 约 1533/1619/1734)。

**后果**:运营必须人工观察域名健康度后手动调高档位;易忘、不及时,养号效率低。

**建议方向**(需产品决策):评估新增「预热自动升档」worker——按 domain 的 total_sent / 停留天数 / 送达率 / 退信率 / 投诉率达标自动升档并写 `level_up` 历史;或明确保持人工、在 UI 增加「达标可升档」提示。

**相关**:`backend/app/services/tenant_messaging_service.py`(配额检查)、`backend/app/workers/sending.py`。

---

## TD-3 · AI 无真实推理(当前为启发式桩)

- **状态**:🔴 未开始
- **性质**:核心功能未实现
- **发现**:2026-07-06

**问题**:系统**没有任何真实 LLM 推理调用**。`backend/app/integrations/openrouter.py` 的 `OpenRouterClient` 只实现了 `/credits`、`/key` 两个余额查询接口,无 `chat/completions`。情报摘要 `backend/app/services/intelligence_service.py` 的 `_build_summary`(约 :360-364)只是截取原文前 240 字,token 数写死 `{input:400,output:100}`(:250),`provider_request_id` 为 `heuristic-intel-*`。`ai_scene_defaults` 的场景模型(`scoring` / `email_generation` / `intelligence_summary` / `data_analysis`)目前只用于「校验有可用模型 + `ai_usage_logs` 记账」,改模型不改变实际产出。其中 `scoring`、`data_analysis` 两个场景连消费方都没有。

**后果**:AI 相关功能(邮件生成、情报摘要、评分辅助)实际未产生 AI 内容;运营 / 客户若期待 AI 效果会落空。

**建议方向**(需产品决策与排期):评估接入真实 OpenRouter `chat/completions`,按 `tenant_ai_provider_configs` 的 key 调用,产出真实内容并如实记账;明确场景优先级——`email_generation`(`tenant_messaging_service.py:205`)、`intelligence_summary`(`intelligence_service.py:341-358`)有消费入口,先接这两个。较大功能,需先定范围。

---

## TD-4 · 数据源腾道命名分裂 tendata / tengdao

- **状态**:🔴 未开始
- **性质**:数据一致性隐患
- **发现**:2026-07-06

**问题**:数据源「腾道」的 `source_type` 有两个不一致写法。种子数据 / DB 用 `tengdao`(`backend/alembic/versions/20260421_0002_seed_and_partitions.py:46-52`),但前端下拉和采集服务代码用 `tendata`(前端 `frontend/apps/admin/src/app/(dashboard)/data-sources/client-page.tsx` 约 :51;采集 `backend/app/services/admin_collection_service.py` 约 :191/:206/:424)。而 `source_type` 的 CHECK 约束已被删除(`20260423_0005_drop_source_type_check.py`),DB 不再校验取值。

**后果**:B 实例现有腾道数据源是种子的 `tengdao`;若运营用前端「新增数据源」选腾道会写 `tendata`,与采集服务期望值对不上,导致「腾道配了凭证却采不到」。`data_source_credentials` 按 `(instance_id, source_type, account_no)` 唯一,`source_type` 不一致会让凭证与采集查询错位。

**建议方向**:统一为单一取值(倾向采集服务用的 `tendata`,或全量迁 `tengdao`,择一),含:迁移已存在的 `data_sources` / `data_source_credentials` 行、改前端下拉、改采集服务常量、评估恢复 `source_type` 白名单校验防止再分裂。涉及生产数据迁移,需在 dev 先验证;先确认 B 实例现有腾道数据源实际 `source_type` 值再定迁移方向。
