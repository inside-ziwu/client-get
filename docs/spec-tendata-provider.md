# 腾道 Provider Spec — 反推采集（海外买家富集）

**版本**: v1.0  
**日期**: 2026-04-30  
**状态**: 反向工程已完成 ✅，待 Phase 2 编码实施  
**参考**: `docs/research/tendata-field-mapping.md` v1.3 / `docs/research/captures/tengdao_*.sh`

---

## 1. Problem Statement

当前 `tendata.py` 使用 `open-api.tendata.cn` + Bearer Token 的实现方式，假设腾道有开放 API，**实际无法调通**。腾道与外贸通形态相同，仅支持 Cookie 会话级 HTTP 爬取。

业务需求：在「反推采集」链路中（Lixiaoyun → 竞对英文名 → 腾道反查 → 海外买家），需要通过腾道采集目标海外买家的 **15 个业务字段**（含联系人），写入 `shared_companies` + `shared_contacts`。

**根本问题**：没有可用的腾道 Provider，整条反推链路的 Stage 2（买家富集）无法执行。

---

## 2. Proposed Solution

### 2.1 整体链路

```
竞对英文名（来自 Lixiaoyun Stage 1）
    │
    ▼
T1  贸易搜索 (data.tendata.cn)
    │  买家列表：name + country（无 tid）
    ▼
BRIEF  公司 BRIEF (bizr.tendata.cn)
    │  → tid（唯一标识）、globizId、aliases[]、website、taxNo、linkedins[]
    ▼
T3  公司详情 (bizr.tendata.cn)
    │  → incorporationDate、employeeNum、industryDesc、websites[]
    ▼
VOT  贸易量统计 (bizr.tendata.cn)
    │  → total_sumOfMoney_sum（3年进出口总额）、total_trades_sum（次数）
    ▼
STATS  供应商分布 (bizr.tendata.cn)
    │  → exporter.results[]（PCB 供应商列表，top-10）
    ▼
T4  联系人采集（3 分支并行，bizr.tendata.cn）
    ├─ T4-LI   v3/contacts/linkedin  → 社媒联系人（姓名+职位+邮箱，emailVerify）
    ├─ T4-NET  v3/contacts/internet  → 邮件联系人（官网爬取，important 字段）
    └─ T4-MORE v2/contacts/more      → 更多联系人（与 LI 重叠，需去重）
    │  三分支按 email 去重，统一为联系人列表
    ▼
写入 shared_companies + shared_contacts
```

### 2.2 鉴权机制

- 纯 Cookie，**无 HMAC/签名**
- 需要字段：`token`（UUID）、`userId`（数字）、`JSESSIONID`
- 两个子域共用同一 Cookie：
  - `data.tendata.cn` — T1 搜索
  - `bizr.tendata.cn` — BRIEF / T3 / VOT / STATS / T4 全部接口
- Cookie 失效特征：HTTP 401 或响应体中含 `"code":401`

### 2.3 接口清单（7 个，全部已抓包）

| # | 名称 | 方法 | Host | 路径 | 关键参数 |
|---|---|---|---|---|---|
| T1 | 贸易搜索 | POST | data.tendata.cn | `/search` | `keyword`=竞对名, `companyType=IMPORTER`, `size` |
| BRIEF | 公司 BRIEF | GET | bizr.tendata.cn | `/api/corp/v2/companies/brief/0` | `name`, `country`（3位码）, `catalog=BUYER`, `source=TRADE` |
| T3 | 公司详情 | GET | bizr.tendata.cn | `/api/corp/v2/companies/0/{tid}` | `tid` |
| VOT | 贸易量统计 | POST | bizr.tendata.cn | `/api/bizr/v1/user/trade/company/report/0/volume_of_trade` | `keyword`, `aliases[]`（来自 BRIEF）, `companyType=IMPORTER`, `reportType=volume_of_trade` |
| STATS | 供应商分布 | POST | bizr.tendata.cn | `/api/bizr/v1/user/trade/company/reports/0/stats` | 同 VOT + `statFields=trades,top_items,exporter` |
| T4-LI | 社媒联系人 | GET | bizr.tendata.cn | `/api/contactx/v3/contacts/linkedin` | `tid`, `globizId`, `linkedInCompanyId`（从 BRIEF.moreInfo.linkedins 提取 slug）|
| T4-NET | 邮件联系人 | GET | bizr.tendata.cn | `/api/contactx/v3/contacts/internet` | `tid`, `companyName`, `website`, `taxNo` |
| T4-MORE | 更多联系人 | GET | bizr.tendata.cn | `/api/contactx/v2/contacts/more` | `tid`, `page`（**从 1 起**）, `size` |

> ⚠️ 关键细节：`tid` 不能客户端构造，必须通过 BRIEF 接口解析返回值获取。

### 2.4 15 个采集字段（业务已确认）

| # | 字段 | 来源 | 覆盖率 |
|---|---|---|---|
| 1 | 公司名称 | BRIEF.name | 100% |
| 2 | 英文名称 | BRIEF.name | 100% |
| 3 | 国家 | BRIEF.country（3位码→中文映射） | 100% |
| 4 | 细分行业 | T3.industryDesc | ~20%，null 时不显示 |
| 5 | 产品标签 | T1.productTag[]（去重） | 有贸易记录时 |
| 6 | 员工人数 | T3.employeeNum | ~20%，null 时不显示 |
| 7 | 官网 | BRIEF.website，无则 T3.websites[0] | ~80% |
| 8 | 数据来源 | 固定值 `"腾道"` | 100% |
| 9 | 有无进出口数据 | 推导：在 T1 搜索结果中出现 = `"有"` | 100% |
| 10 | 进出口总额（3年） | VOT.stats.total_sumOfMoney_sum | 100% |
| 11 | 进出口次数 | VOT.stats.total_trades_sum | 100% |
| 12 | 联系人数 | T4 三分支去重后计数 | ~70% |
| 13 | 成立时间 | T3.incorporationDate | ~40% |
| 14 | PCB 供应商 | STATS.exporter.results[].\_\_gk（去重） | 搜索范围内 |
| 15 | 更新时间 | 系统采集入库时间戳 | 100% |

### 2.5 联系人统一格式

三分支原始 schema 不同，合并后统一为：

| 字段 | T4-LI 来源 | T4-NET 来源 | T4-MORE 来源 |
|---|---|---|---|
| 姓名 | `name` | `name`（域名，通常为 null） | `name` |
| 职位 | `position` | null | `position` |
| 邮箱 | `email` / `personalEmail1.email`（去 `^ESD`） | `email` | `email` |
| 重要程度 | null | `important`（HIGH_HIGH 等） | null |
| 来源描述 | null | `description` | null |
| 是否验证 | `emailVerify`（WHITE / BLACK） | `emailVerify`（通常 null） | `status`（VALID / INVALID） |

**去重规则**：
1. 端点内：v3 用 `uniqueKey`，v2 用 `id`
2. 跨端点：以 `email` 兜底去重
3. 合并策略：同一 email 多端点重复时，保留有姓名+职位的条目，补充另一端点的重要程度/来源描述

---

## 3. Technical Constraints

| 约束 | 说明 |
|---|---|
| Cookie 会话鉴权 | 无 HMAC/签名，`token`+`userId`+`JSESSIONID` 三字段缺一不可 |
| 请求延迟 | 3-5 秒随机延迟（与外贸通相近），避免频控封号 |
| tid 依赖 BRIEF | T1 搜索结果不含 tid，必须先调 BRIEF 解析 |
| aliases 必传 | VOT / STATS 调用必须传 BRIEF 返回的 `aliases[]`，否则统计口径偏小 |
| T4-MORE 版本差异 | 路径为 `v2`（非 v3），`page` 从 1 起（非 0），`atts` 为 null |
| internet 联系人特点 | `name` = 域名（非真人），`emailVerify` 通常 null，以 `important` 字段替代质量判断 |
| Cookie 失效处理 | HTTP 401 → 暂停该数据源所有任务 + 告警运营，运营手动更新 Cookie 后恢复 |
| 覆盖率低的字段 | `industryDesc`、`employeeNum`、`incorporationDate` 在测试样本中缺值率高，存 `raw_payload`，UI 按 null 判断是否展示 |

---

## 4. Non-goals

- ❌ 不使用 `open-api.tendata.cn`（无开放 API，当前 tendata.py 的实现方式必须废弃）
- ❌ 不采集 `ind_comm` / `other` / `dept` 三个联系人子端点（信息量有限，Phase 2 按需补充）
- ❌ 不采集公司 Logo（业务已移除该字段）
- ❌ 不采集工厂性质（`companyType`，覆盖率低，业务已移除）
- ❌ 不做按竞对口径的进出口统计（VOT/STATS 使用全量口径，即买家所有供应商，不过滤特定竞对）
- ❌ 不做实时/按需采集，仅批量计划任务
- ❌ 不做租户自带腾道账号（Phase 2 期间凭证由平台运营统一维护）

---

## 5. Success Criteria

| # | 验收标准 |
|---|---|
| 1 | 给定竞对英文名，能跑通完整 7 接口链路，买家信息写入 `shared_companies` |
| 2 | 15 个字段按映射表正确落库；覆盖率低的字段（行业/员工/成立时间）为 null 时不报错 |
| 3 | T4 三分支联系人采集后，按 email 去重，写入 `shared_contacts`，`contacts_count` = 去重后实际条数 |
| 4 | 联系人统一格式 6 个字段正确映射（缺失字段填 null，不丢数据） |
| 5 | Cookie 失效（401）时任务暂停并触发运营告警，不抛未捕获异常 |
| 6 | 完整 API 响应存入 `raw_payload` JSONB（便于后续字段补全） |
| 7 | 单公司采集（T1→T4 全链路）耗时 ≤ 60 秒（含随机延迟） |
