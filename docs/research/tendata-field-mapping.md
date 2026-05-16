# 腾道采集字段映射表 v1.3

**日期**: 2026-04-30  
**状态**: ✅ 业务已确认  
**数据来源**: T1 Search + BRIEF + T3 ALL + T4 Contacts（6子端点） + volume_of_trade + stats（7 个已抓包确认接口）

---

## 1. 字段映射总表（最终版）

| # | 字段名 | API | 字段路径 | 覆盖率 | 备注 |
|---|---|---|---|---|---|
| 1 | 公司名称 | BRIEF | `name` | ✅ 100% | 标准化英文名 |
| 2 | 英文名称 | BRIEF | `name` | ✅ 100% | 同公司名称字段 |
| 3 | 国家 | BRIEF | `country`（3位码，映射为中文） | ✅ 100% | MYS→马来西亚 |
| 4 | 细分行业 | T3 ALL | `industryDesc` | ❌ ~20% | 多数 null，存 raw_payload，UI 判空不显示 |
| 5 | 产品标签 | T1 Search | 聚合 `productTag[]`（去重） | ✅ 有贸易记录时 | 贸易记录级字段 |
| 6 | 员工人数 | T3 ALL | `employeeNum` | ❌ ~20% | 多数 null，存 raw_payload，UI 判空不显示 |
| 7 | 官网 | BRIEF / T3 ALL | `website` / `websites[0]` | ✅ ~80% | 优先 BRIEF，无则取 T3 ALL |
| 8 | 数据来源 | 固定值 | `"腾道"` | ✅ 100% | 平台标识，非 API 动态字段 |
| 9 | 有无进出口数据 | 推导 | 在 T1 搜索结果中出现 = true | ✅ 100% | |
| 10 | 进出口总额（3年） | volume_of_trade | `stats.total_sumOfMoney_sum` | ✅ 100% | 全量口径（所有供应商） |
| 11 | 进出口次数 | volume_of_trade | `stats.total_trades_sum` | ✅ 100% | 全量口径 |
| 12 | 联系人数 | T4 | `atts.contactTotal` | ✅ 有 LinkedIn 时 | ~70% 覆盖 |
| 13 | 成立时间 | T3 ALL | `incorporationDate` | ⚠️ ~40% | 依赖工商注册数据 |
| 14 | PCB 供应商 | T1 Search + stats | 聚合 `exporter`（去重） | ✅ 搜索范围内 | 多 keyword 采集后聚合 |
| 15 | 更新时间 | 系统时间 | 采集入库时间戳 | ✅ 100% | |

---

## 2. 真实数据示例

### 示例 A：FILTERMATION MFG SDN BHD（马来西亚）

> 数据来源：T1 搜索（exporter=FINEST PCB SHENZHEN LIMITED）+ BRIEF + T4

| 字段 | 值 | 来源 |
|---|---|---|
| 公司名称 | FILTERMATION MFG SDN BHD | BRIEF.name |
| 公司 LOGO | https://media.licdn.com/dms/image/v2/C510BAQEuvuLThO4Vhw/... | BRIEF.images[0] |
| 英文名称 | FILTERMATION MFG SDN BHD | BRIEF.name |
| 国家 | 马来西亚（MYS） | BRIEF.country |
| 细分行业 | —（null） | T3 ALL.industryDesc |
| 产品标签 | GARAGE BRIDGE PCBA | T1.productTag（去重后） |
| 工厂性质 | —（null） | T3 ALL.companyType |
| 公司规模 | —（null） | T3 ALL.employeeNum |
| 官网 | filtermation-mfg.com | BRIEF.website |
| 数据来源 | malaysia_pro | T1.database（去重） |
| 有无进出口数据 | ✅ 是 | 推导 |
| 进出口总额（3年） | $3,425.58（样本 1 条记录） | T1.sumOfUSD 累加 |
| 进出口次数 | 1 条（样本范围） | T1 记录数 |
| 联系人数 | 21 人 | T4.atts.contactTotal |
| 公司成立时间 | —（未抓 T3 ALL，待确认） | T3 ALL.incorporationDate |
| PCB 供应商 | FINEST PCB SHENZHEN LIMITED | T1.exporter（去重） |
| 手动录入栏 | — | — |
| 更新时间 | 2025-09-12（BRIEF 入库时间） | BRIEF.createdDate |

**T4 联系人示例（前2条）：**

| 姓名 | 职位 | 标签 | 工作邮件 | 个人邮件 | 邮件质量 |
|---|---|---|---|---|---|
| Harith Nordin | Director | EXECUTIVE | harith@nordintech.com | harith.nordin@gmail.com | WHITE ✅ |
| Aizat Abd Muttalib | Production Manager | UNSPECIFIED | aizat@nordintech.com | — | WHITE ✅ |

---

### 示例 B：POSIFLOW RETAIL PRIVATE LTD.（印度）

> 数据来源：T1 搜索 + BRIEF + T3 ALL（字段更丰富）

| 字段 | 值 | 来源 |
|---|---|---|
| 公司名称 | POSIFLOW RETAIL PRIVATE LTD. | BRIEF / T3 ALL.name |
| 公司 LOGO | — | BRIEF.images（未抓到 logo） |
| 英文名称 | POSIFLOW RETAIL PRIVATE LTD. | — |
| 国家 | 印度（IND） | BRIEF.country |
| 细分行业 | —（null） | T3 ALL.industryDesc |
| 产品标签 | BARE PCB | T1.productTag |
| 工厂性质 | —（null） | T3 ALL.companyType |
| 员工人数 | —（null） | T3 ALL.employeeNum |
| 官网 | posiflow.in | T3 ALL.websites[0] |
| 数据来源 | 腾道 | 固定值 |
| 有无进出口数据 | 有 | 推导（在 T1 搜索结果中出现） |
| 进出口总额（3年） | $19,041,400.37 | volume_of_trade.stats.total_sumOfMoney_sum |
| 进出口次数 | 1,488 次 | volume_of_trade.stats.total_trades_sum |
| 联系人数 | 2（去重后） | T4 多子端点采集后去重 |
| 成立时间 | 2023-10-25 | T3 ALL.incorporationDate ✅ |
| PCB 供应商 | FINEST PCB SHENZHEN LIMITED | T1.exporter |
| 更新时间 | 2026-04-30T06:04:11 | T3 ALL.companyBasicInfo.updatedTime |

**T4 联系人明细（去重后 2 条，统一格式）：**

| 姓名 | 职位 | 邮箱 | 重要程度 | 来源描述 | 是否验证 |
|---|---|---|---|---|---|
| Kunal S. | Head of Marketing | kunal@posiflow.in | — | — | VALID ✅ |
| —（域名非人名） | — | posiflow.in@gmail.com | HIGH_HIGH | Discover Posiflow cutting-edge POS... | — |

> 去重：社媒(linkedin) + 更多(more) 均返回 Kunal S. / kunal@posiflow.in → 合并保留 1 条；邮件(internet) 返回域名邮箱 → 独立保留。

---

## 3. 联系人采集架构（T4 完整）

### 3.1 子端点一览

| 子端点 | 路径版本 | 参数 | 特点 |
|---|---|---|---|
| 社媒联系人 | `v3/contacts/linkedin` | `globizId`, `tid`, `linkedInCompanyId` | 需 BRIEF.moreInfo.linkedins；有 `personalEmail1` |
| 邮件联系人 | `v3/contacts/internet` | `tid`, `companyName`, `website`, `taxNo` | 官网爬取，name=域名而非真人 |
| 更多联系人 | **v2**/contacts/more | `tid`, `page`（从1起）, `size` | `status:VALID` 而非 `emailVerify:WHITE` |
| 工商联系人 | `v3/contacts/ind_comm` | `tid` | 来自工商注册数据（未抓） |
| 其他联系人 | `v3/contacts/other` | `tid` | 其他来源（未抓） |
| 部门联系人 | `v3/contacts/dept` | `tid` | 按部门分类（未抓） |
| ~~用户CRM~~ | `dmx-edm/v1/users/contacts` | — | **非采集端点**，用户自己的 EDM 库，跳过 |

### 3.2 统一联系人格式

> 三个分支原始字段不同，采集后统一映射为以下格式，无值填 null：

| 统一字段 | 社媒(linkedin v3) | 邮件(internet v3) | 更多(more v2) |
|---|---|---|---|
| 姓名 | `name` | `name`（域名，通常忽略） | `name` |
| 职位 | `position` | null | `position` |
| 邮箱 | `email` / `personalEmail1.email`（去掉`^ESD`） | `email` | `email` |
| 重要程度 | null | `important` | null |
| 来源描述 | null | `description` | null |
| 是否验证 | `emailVerify`（WHITE/BLACK） | `emailVerify`（通常 null） | `status`（VALID/INVALID） |

### 3.3 去重规则

1. **端点内**：v3 用 `uniqueKey`，v2 用 `id`
2. **跨端点**：以 `email` 兜底去重（同邮箱保留信息最全的一条）
3. **合并策略**：同一 email 出现在多端点时，优先保留有 `姓名+职位` 的条目，补充另一端点的 `重要程度/来源描述`

---

## 4. 待确认事项

### 4.1 进出口总额/次数口径
**当前口径（已采用）**：volume_of_trade 全量口径（买家全部供应商，含 PCB 及非 PCB）  
**备注**：stats 接口的 `exporter.results` 可看到具体供应商分布，FINEST PCB 未必在 top-10

### 4.2 字段覆盖率较低的字段
- **细分行业**：industryDesc 在测试样本中均为 null，存 raw_payload，UI 按 null 判断是否展示
- **员工人数**：employeeNum 同上，部分欧美大公司可能有值
- **成立时间**：incorporationDate ~40% 覆盖，视工商注册数据完整度

---

## 5. 数据模型草稿（shared_companies 相关字段）

```sql
-- 腾道专属字段（存入 JSONB raw_payload 或独立列）
tendata_tid           TEXT           -- BRIEF.tid
tendata_globiz_id     TEXT           -- BRIEF.globizId  
company_name_std      TEXT           -- BRIEF.name
company_name_local    TEXT           -- BRIEF.localName / T3.companyBasicInfo.localName
country_code3         CHAR(3)        -- BRIEF.country
website               TEXT           -- BRIEF.website
tax_no                TEXT           -- BRIEF.taxNo
incorporation_date    DATE           -- T3.incorporationDate
employee_num          INT            -- T3.employeeNum（可 null）
industry_desc         TEXT           -- T3.industryDesc（可 null）
logo_url              TEXT           -- BRIEF.images[0]
trade_sources         TEXT[]         -- T1.database 去重列表
product_tags          TEXT[]         -- T1.productTag 去重列表
pcb_suppliers         TEXT[]         -- T1.exporter 去重列表（关联的中国竞对）
trade_amount_3y_usd   NUMERIC        -- volume_of_trade.stats.total_sumOfMoney_sum（全量口径）
trade_count           INT            -- volume_of_trade.stats.total_trades_sum（全量口径）
contacts_count        INT            -- T4 多端点去重后总数
raw_payload           JSONB          -- 完整 API 响应存档（各端点合并）
```
