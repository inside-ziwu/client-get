# Codex Review · 07-v3-scope-final · Round 2

> 审查日期：2026-05-06
> 审查范围：仅验证第 1 轮报告中的 9 处 finding 是否已修复
> 不审范围：不重审完整性 / 准确性 / 冲突 3 类；不修改被审文件
> 被审文件：`_control/v3/07-v3-scope-final.md`

## 0. 总体结论

第 1 轮列出的 9 处 finding 已全部修复：2 个 High、5 个 Medium、2 个 Low 均能在 `07-v3-scope-final.md` 中找到明确修订证据。当前不再因为这 9 处问题阻止签字；但本轮发现 1 个新引入的低风险残留：`07` §9 PM Review Checklist 仍保留旧数字口径，与已修复后的 §2 / §5 汇总不一致，建议签字前顺手改掉。

## 1. 9 处修复验证表

| ID | 修复点 | 状态 | 文件:行号 证据 |
|---|---|:-:|---|
| High-01 | `07` §3 业务规则 → 实施位置交叉表扩展为 26 行，并覆盖第 1 轮指出的 business-goals §5 漏项 | ✅ | `_control/v3/07-v3-scope-final.md:91-120`。表格从关键词到 Sealos 部署共 26 条业务规则；关键漏项已分别落在 `:95-99`、`:101-104`、`:111-112`、`:117-119`。 |
| High-01.a | 覆盖“关键词仅英文 + 配置者租户 + 数量上限无” | ✅ | `_control/v3/07-v3-scope-final.md:95-96`：关键词英文/归一化、租户配置、无后端限制。 |
| High-01.b | 覆盖“反推每日上限 1000 条 / 数据源” | ✅ | `_control/v3/07-v3-scope-final.md:99`：collection scheduler 限速 + `data_source_credentials.daily_limit`。 |
| High-01.c | 覆盖“励销云不入干净库” | ✅ | `_control/v3/07-v3-scope-final.md:101`：`source_type='lixiaoyun'` 标 done 不入 clean。 |
| High-01.d | 覆盖“客户列表 1 行 = 1 公司 + 来源标签精准” | ✅ | `_control/v3/07-v3-scope-final.md:103-104`：clean/tenant 去重 + `sources` 字段 + UI 展示。 |
| High-01.e | 覆盖“回信路径 / 发送速率” | ✅ | `_control/v3/07-v3-scope-final.md:111-112`：`Reply-To = From`；sending worker 受 `domain_warmup_status.daily_limit` 限速。 |
| High-01.f | 覆盖“内容来源 4 选 1” | ✅ | `_control/v3/07-v3-scope-final.md:119`：tenant-send-plans-new 内容选择 UI + 4 路 API。 |
| High-01.g | 覆盖“多步骤序列第 N 轮发未发过的其他联系人” | ✅ | `_control/v3/07-v3-scope-final.md:117`：sequence 推进逻辑 + `email_send_locks` 去重。 |
| High-02 | `07` §6.1 拆分为 §6.1.1 原文 5 项 + §6.1.2 D-041 补充验收 | ✅ | `_control/v3/07-v3-scope-final.md:185-197`。§6.1.1 明确“与 business-goals §7.2 一致的 5 项”；§6.1.2 明确 D-041 非 §7.2 原文。 |
| Medium-01 | 部署单元数量统一为 9 部署单元 | ✅ | `_control/v3/07-v3-scope-final.md:86` 写“Sealos 9 部署单元（PostgreSQL + admin + tenant + backend + 4 原 worker + cleanup_service）”；`:120` 同样写“§5.5 Sealos 9 部署单元”。 |
| Medium-02 | `tenant-intelligence` C2 状态改为综合 MISSING（前端 PARTIAL） | ✅ | `_control/v3/07-v3-scope-final.md:62`：现状列为“C2 综合 MISSING（前端 PARTIAL）”。 |
| Medium-03 | `admin-collection-tasks` 不再引用“codex B-01”，改为具体代码行号 + 缺口说明 | ✅ | `_control/v3/07-v3-scope-final.md:42`：引用 `admin/CollectionTasks/index.tsx:230-302`，并说明缺口为按 D-035 禁用 direct channel + 后端防御性拒绝。 |
| Medium-04 | `07` §3 增加发送速率 / 预热档位限速行 | ✅ | `_control/v3/07-v3-scope-final.md:112`：`§5.4 发送速率（受预热档位约束，租户不能突破）→ sending worker + domain_warmup_status.daily_limit`。 |
| Medium-05 | `4 worker base class` 现状改为 C8-G5 MISSING，不再写 C8 SKELETON | ✅ | `_control/v3/07-v3-scope-final.md:85`：现状为“C8-G5 MISSING（监控 / 日志 / 重试 / 幂等待补）”。 |
| Low-01 | Admin 数字口径统一为“Admin 11 模块：开发 6 / 不做 5” | ✅ | `_control/v3/07-v3-scope-final.md:52`：明确“本期开发 6 个（含 collection-tasks 复核）/ 不做 5 个”。 |
| Low-02.a | Tenant 数字口径统一为“Tenant 13 模块：开发 6 / 极简 1 / 不做 6” | ✅ | `_control/v3/07-v3-scope-final.md:72`：明确“本期开发 6 个 / 极简 1 个（dashboard）/ 不做 6 个”。 |
| Low-02.b | §5 后说明改为“24 = 12 开发 + 1 极简 + 11 不做”，并列明明细 | ✅ | `_control/v3/07-v3-scope-final.md:173-179`：开发 12、极简 1、已 PASS 不开发 11；admin 5 + tenant 6 明细已列出。 |

### 1.1 High-01 细项 grep 记录

- 目标：只确认第 1 轮指出的业务规则漏项是否写入 `07` §3。
- 结论：已写入。
- 行数核对：`07` §3 的业务规则表从 `_control/v3/07-v3-scope-final.md:95` 到 `:120`。
- 表格行数：共 26 条业务规则行。
- 关键词英文：见 `_control/v3/07-v3-scope-final.md:95`。
- 关键词归一化：见 `_control/v3/07-v3-scope-final.md:95`。
- 配置者为租户：见 `_control/v3/07-v3-scope-final.md:96`。
- 数量上限无：见 `_control/v3/07-v3-scope-final.md:96`。
- 跨租户复用：见 `_control/v3/07-v3-scope-final.md:97`。
- 反推数据源：见 `_control/v3/07-v3-scope-final.md:98`。
- 每日上限 1000 条 / 数据源 / 天：见 `_control/v3/07-v3-scope-final.md:99`。
- raw → clean → tenant 分发：见 `_control/v3/07-v3-scope-final.md:100`。
- 励销云不入 clean：见 `_control/v3/07-v3-scope-final.md:101`。
- 干净库唯一来源 = 腾道：见 `_control/v3/07-v3-scope-final.md:102`。
- 客户列表 1 行 = 1 公司：见 `_control/v3/07-v3-scope-final.md:103`。
- 来源标签精准：见 `_control/v3/07-v3-scope-final.md:104`。
- 10 项筛选：见 `_control/v3/07-v3-scope-final.md:105`。
- 双层评分：见 `_control/v3/07-v3-scope-final.md:106`。
- PCB 7 维与等级阈值：见 `_control/v3/07-v3-scope-final.md:107`。
- 租户私有状态层：见 `_control/v3/07-v3-scope-final.md:108`。
- EngageLab 通道：见 `_control/v3/07-v3-scope-final.md:109`。
- 域名验证：见 `_control/v3/07-v3-scope-final.md:110`。
- 回信路径：见 `_control/v3/07-v3-scope-final.md:111`。
- 发送速率与预热档位：见 `_control/v3/07-v3-scope-final.md:112`。
- 联系人级 4 态：见 `_control/v3/07-v3-scope-final.md:113`。
- 投递监控 6 指标：见 `_control/v3/07-v3-scope-final.md:114`。
- 联系人职位分类：见 `_control/v3/07-v3-scope-final.md:115`。
- 自动取联系人：见 `_control/v3/07-v3-scope-final.md:116`。
- 多步骤序列第 N 轮发未发过联系人：见 `_control/v3/07-v3-scope-final.md:117`。
- 邮件计划结构：见 `_control/v3/07-v3-scope-final.md:118`。
- 内容来源 4 选 1：见 `_control/v3/07-v3-scope-final.md:119`。
- Sealos 9 部署单元：见 `_control/v3/07-v3-scope-final.md:120`。

### 1.2 High-02 细项 grep 记录

- 目标：确认 §6.1 是否不再把 D-041 混入 business-goals §7.2 原文 5 项。
- 结论：已拆分。
- §6.1 标题仍为业务侧成功标准：`_control/v3/07-v3-scope-final.md:185`。
- §6.1.1 标题明确“与 business-goals §7.2 一致的 5 项”：`_control/v3/07-v3-scope-final.md:187`。
- 原文 5 项分别位于 `_control/v3/07-v3-scope-final.md:189-193`。
- §6.1.2 标题明确“补充验收”：`_control/v3/07-v3-scope-final.md:195`。
- D-041 指标位于 `_control/v3/07-v3-scope-final.md:197`。
- D-041 标注为“非 §7.2 原文”：`_control/v3/07-v3-scope-final.md:195`。

### 1.3 Medium / Low 细项 grep 记录

- Medium-01：§2.3 部署行写 9 部署单元，见 `_control/v3/07-v3-scope-final.md:86`。
- Medium-01：§3 业务规则表也写 9 部署单元，见 `_control/v3/07-v3-scope-final.md:120`。
- Medium-01：两个位置口径一致。
- Medium-02：tenant-intelligence 行写 C2 综合 MISSING，见 `_control/v3/07-v3-scope-final.md:62`。
- Medium-02：同一行括号保留“前端 PARTIAL”，没有再把综合状态写成 PARTIAL。
- Medium-03：admin-collection-tasks 行已删除“codex B-01”字样，见 `_control/v3/07-v3-scope-final.md:42`。
- Medium-03：该行改为具体前端代码行号 `admin/CollectionTasks/index.tsx:230-302`。
- Medium-03：该行同时写出剩余缺口“禁用 direct channel + 后端防御性拒绝”。
- Medium-04：发送速率单独成行，见 `_control/v3/07-v3-scope-final.md:112`。
- Medium-04：实施位置包含 `sending worker`。
- Medium-04：实施位置包含 `domain_warmup_status.daily_limit`。
- Medium-05：4 worker base class 行不再写 C8 SKELETON，见 `_control/v3/07-v3-scope-final.md:85`。
- Medium-05：该行状态改为 C8-G5 MISSING。
- Medium-05：缺口文字列出监控 / 日志 / 重试 / 幂等。
- Low-01：Admin 汇总行已为 11 模块、开发 6、不做 5，见 `_control/v3/07-v3-scope-final.md:52`。
- Low-02：Tenant 汇总行已为 13 模块、开发 6、极简 1、不做 6，见 `_control/v3/07-v3-scope-final.md:72`。
- Low-02：§5 汇总总数为 24 = 12 开发 + 1 极简 + 11 不做，见 `_control/v3/07-v3-scope-final.md:173`。
- Low-02：12 个开发明细见 `_control/v3/07-v3-scope-final.md:175`。
- Low-02：1 个极简明细见 `_control/v3/07-v3-scope-final.md:176`。
- Low-02：11 个不开发明细见 `_control/v3/07-v3-scope-final.md:177-179`。

## 2. 新引入问题

| ID | 严重度 | 问题 | 证据 | 建议 |
|---|---|---|---|---|
| R2-Low-01 | Low | `07` §9 PM Review Checklist 仍保留旧数字口径，与 §2 / §5 已修复后的口径不一致。 | `_control/v3/07-v3-scope-final.md:233-234` 仍写“Admin 11 模块本期范围分类（5 做 / 6 不做）”和“Tenant 13 模块本期范围分类（6 做 / 7 不做）”；但正确口径已在 `:52`、`:72`、`:173-179`。 | 签字前改为“Admin 6 开发 / 5 不做”和“Tenant 6 开发 / 1 极简 / 6 不做”。 |

## 3. 给用户的无技术背景版摘要

1. 上轮 9 个问题都已经修好；这 9 项本身不再挡签字。
2. 最重要的“业务规则落到哪里实现”现在已经补成完整交叉表，之前漏掉的限速、回信路径、内容来源、联系人轮发等细节都写进去了。
3. 还有一个小尾巴：最后的签字检查清单里数字没同步，正文已经是对的，签字前把清单两行改掉即可。
