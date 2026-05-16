# PCB 反推采集 — 流程确认 + HTTP 抓包指南

**版本**: v0.2
**日期**: 2026-04-30
**变更**: v0.1 中我对腾道/外贸通流程的理解有误，本版以用户原文为准
**协作模式**: 我列**抓包清单**，你登录后用 Chrome DevTools 抓 curl 给我

---

## 1. 总览（已修订）

```
[Stage 1] 励销云                    [Stage 2] 腾道                              [Stage 3] 外贸通
✅ 已实现，引用现有代码                数据通 → 贸易记录                          客户发现 → 数据获客 → 海关数据
（lixiaoyun.py）                    全球搜 + 进口 131 个数据源                  按公司 + 供应商 Tab
                                    时间: 2020-01-01 至今                       时间: 2001-01-01 至今
                                    出口商名称 = 同行英文名                      排除物流公司
                                       ↓                                          ↓
                                    进口商列表                                   公司搜索结果
                                       ↓ 每个点进去                                ↓ 点公司进详情 → 海关数据 → 出口记录
                                    进口商详情                                   采购商列表
                                                                                  ↓ 每个采购商点进去
                                                                                采购商详情
```

---

## 2. Stage 1 — 励销云（已实现）

> 直接引用现有代码：`backend/app/integrations/collection/lixiaoyun.py`
>
> 本期不需要重做调研、不需要重抓 curl。Phase 2 实施时直接复用并适配新分层（采集只写 shared_*，不写 tenant_companies）。

---

## 3. Stage 2 — 腾道（按用户原文确认）

### 3.1 入口与表单

| 项 | 值 |
|---|---|
| 顶部菜单 | **数据通 → 贸易记录** |
| 数据源 | **全球搜 + 进口 131 个数据源** |
| 时间范围 | **2020-01-01 至今** |
| 出口商名称 | **同行英文名**（即 Stage 1 拿到的英文名） |
| 其他过滤 | （未指定，按默认） |

### 3.2 操作动作

1. 进入「数据通 → 贸易记录」
2. 设置数据源为「全球搜」+ 勾选「进口 131 个数据源」
3. 时间范围 `2020-01-01 ~ 今天`
4. 「出口商名称」字段填同行英文名（如 `FINEST PRINTED CIRCUIT BOARD LTD`）
5. 提交搜索 → 得到一组贸易记录
6. 关注「**进口商名称（标准）**」列 → 这一列的每个值就是**海外买家**
7. 每个进口商点击进详情页 → 提取数据

### 3.3 我对流程的理解（请你 ✅ / ❌）

- ✅ / ❌ 「贸易记录」是按贸易**事件**展示，不是按公司聚合。一个进口商可能在多笔贸易记录里重复出现，需要在客户端按「进口商名称（标准）」去重
- ✅ / ❌ 「进口商名称（标准）」是字段名，「标准」表示这是清洗过的标准化公司名（用于精确匹配/去重）
- ✅ / ❌ 点击进口商打开的「详情页」是**进口商公司画像**，含公司基本信息 + 联系人 + 进出口分析等（参考 v0.1 中 image_08 的页面结构）
- ✅ / ❌ 点击进口商详情后是**新页面**还是**侧边抽屉/弹窗**？这影响有几个独立 URL

---

## 4. Stage 3 — 外贸通（按用户原文修订）

### 4.1 路径

```
客户发现 → 数据获客 → 海关数据
   → 按公司                   ← Tab
   → 输入: 同行英文名
   → 供应商 Tab               ← Tab
   → 时间范围: 2001-01-01 至今
   → 排除物流公司             ← 勾选
   → 点击「查询」
       ↓
   公司搜索结果列表（中国供应商，匹配同行英文名）
       ↓
   点击公司名称进详情页
       ↓
   海关数据 Tab → 出口记录子 Tab
       ↓
   出口记录表格中「采购商」列 = 海外买家
       ↓
   每个采购商点进详情页 → 提取数据
```

### 4.2 我对流程的理解（请你 ✅ / ❌）

- ✅ / ❌ 「按公司」搜索时，搜索框里填的是**中国同行的英文名**，不是产品/HSCode
- ✅ / ❌ 搜索后返回的是**中国供应商记录**（即同行公司在外贸通的对应条目）。可能匹配多条
- ✅ / ❌ 进入某条公司后，「海关数据 → 出口记录」中的「采购商」列就是要的海外买家
- ✅ / ❌ 采购商详情页（点采购商打开的页）是**新页面**还是**弹窗/抽屉**

---

## 5. HTTP 抓包指南（你的操作步骤）

### 5.1 浏览器准备

1. **Chrome / Edge** 打开目标网站，登录账号
2. 按 `F12` 打开 DevTools，切到 **Network** Tab
3. 顶部勾选两项：
   - ✅ **Preserve log**（页面跳转/刷新后保留请求记录）
   - ✅ **Disable cache**
4. 顶部 Filter 行选 **Fetch/XHR**（只看接口请求，过滤掉 html/css/js/img）
5. 准备好后，点击 DevTools 左上的 🚫 图标 **Clear**（清空旧记录）

### 5.2 抓单个 curl 的标准动作

每抓一个端点都按这套标准：

1. **Clear** 清空 Network 面板
2. 在网页上**做一个动作**（如点搜索按钮、点公司名进详情、翻页）
3. Network 面板出现新的 XHR/Fetch 请求
4. 找到主请求（看 URL 是 API 路径，不是 image/font 等资源；Method 通常是 POST 或带参的 GET）
5. **右键该请求 → Copy → Copy as cURL (bash)**
6. 粘贴到文本文件保存，文件名按下面 §6 清单命名

### 5.3 怎么判断哪个请求是「主请求」

- URL 看起来像 API 路径：含 `/api/` `/v1/` `/openapi/` 等关键字
- 响应是 JSON（点 Response Tab 看，最上面括号是 `{` 或 `[`）
- 响应里有列表数据（看 Preview 能看到公司名/进口商名等业务字段）

如果**多个请求看起来都像主请求**：把它们都抓下来，命名加 `_alt1.sh` `_alt2.sh`，我来分析。

### 5.4 脱敏建议

**Cookie 是敏感信息**，但完整 cookie 决定了请求能否成功。两种方案：

- **方案 A（首选）**: 直接给我原始 curl，我承诺只用于本项目分析，分析完后让你重置 cookie。前提是你信任本协作环境。
- **方案 B**: 把 cookie 中的关键字段（如 `QIYE_TOKEN=xxx`、`Authorization: ...` 这类）替换为 `<COOKIE_QIYE_TOKEN>`、`<AUTH_TOKEN>`，**保留所有 header 名 + 顺序**，我据此推断协议。

> 不论哪种，**Token / signature / timestamp** 这些动态值我不需要真实值——我看 header 名和长度就能推断。**重点是请求体（POST body）的 JSON 结构**和**返回体的 JSON 结构**。

### 5.5 同时给我返回体 sample

光给 curl 不够，请同时给我**这条请求的响应内容**（DevTools → 选中请求 → Response Tab → 全选复制，或者右键 → Copy → Copy response）。

→ 命名：`<curl 同名>_response.json`

---

## 6. 待你提供的 curl 清单

按这个清单一个一个抓，每个抓两份：`*.sh`（curl）+ `*_response.json`（响应）。

### 6.1 腾道（共 4-5 个 curl）

| # | 文件名 | 抓取动作 | 关键参数 |
|---|---|---|---|
| T1 | `tengdao_search_p1.sh` | 数据通 → 贸易记录，配置好搜索条件后第一次点查询 | 出口商名称 = 一个真实同行英文名（找一个能搜出 100+ 条记录的） |
| T2 | `tengdao_search_p2.sh` | T1 之后翻到第 2 页 | 用同一个出口商名称，分页参数自动变化 |
| T3 | `tengdao_importer_detail.sh` | T1 列表中点击某个「进口商名称（标准)」 | 选一个有数据的进口商（如印度/越南公司） |
| T4 | `tengdao_importer_contacts.sh` | T3 详情页里点击「联系人」Tab（如果有） | 关注联系人列表是否分页 |
| T5（可选）| `tengdao_data_sources.sh` | 「全球搜 + 进口 131 个数据源」选项展开时的请求（如果是动态加载） | — |

### 6.2 外贸通（共 5-6 个 curl）

| # | 文件名 | 抓取动作 | 关键参数 |
|---|---|---|---|
| W1 | `waimao_company_search_p1.sh` | 客户发现 → 数据获客 → 海关数据 → 按公司 + 供应商 Tab，输入同行英文名 + 排除物流，点查询 | 同行英文名 = 真实英文名 |
| W2 | `waimao_company_search_p2.sh` | W1 翻页 2 | — |
| W3 | `waimao_company_detail.sh` | W1 列表中点击某个公司名进详情页 | — |
| W4 | `waimao_export_records_p1.sh` | W3 公司详情中点「海关数据 → 出口记录」 | 关注表格里采购商列 |
| W5 | `waimao_buyer_detail.sh` | W4 表格中点击某个采购商名 | — |
| W6（可选）| `waimao_buyer_contacts.sh` | W5 采购商详情里点联系人 Tab（如果有） | — |

### 6.3 投递方式

把 `*.sh` 和 `*_response.json` 全部放到 `docs/research/captures/` 目录下，我从这里读取分析。

```
docs/research/captures/
├── tengdao_search_p1.sh
├── tengdao_search_p1_response.json
├── tengdao_search_p2.sh
├── tengdao_search_p2_response.json
├── tengdao_importer_detail.sh
├── tengdao_importer_detail_response.json
├── tengdao_importer_contacts.sh
├── tengdao_importer_contacts_response.json
├── waimao_company_search_p1.sh
├── waimao_company_search_p1_response.json
├── waimao_company_search_p2.sh
├── waimao_company_search_p2_response.json
├── waimao_company_detail.sh
├── waimao_company_detail_response.json
├── waimao_export_records_p1.sh
├── waimao_export_records_p1_response.json
├── waimao_buyer_detail.sh
└── waimao_buyer_detail_response.json
```

---

## 7. 拿到 curl 后我会做什么

针对每对 `(curl, response)`，我会输出：

1. **接口契约**：URL / Method / 关键 Header / Body 结构 / 响应 JSON 路径
2. **鉴权机制**：Cookie / Token / Signature 的形态，是否需要刷新机制
3. **分页参数**：page / size / cursor 等
4. **数据字段映射表**：响应字段 → CollectionPayload / shared_companies 的映射
5. **限流提示**：从响应 header 推断的 rate limit 信号（如果有）
6. **Provider 实现伪代码**：基于真实接口结构，给出 `WaiMaoTongCollectionProvider` / `TendataCollectionProvider` 的核心方法签名 + 调用顺序

这一步完成后，反向工程 R-1 / R-2 算正式收尾，可以进入 Phase 2 实施规划 + plan-eng-review。

---

## 8. 仍在 Spec 层待澄清的产品问题（不阻塞抓包，但实施前必答）

不影响抓包动作，但实施前需要回答（与 v0.1 §7 同源，按修订流程压缩）：

1. **励销云的「线路板/电路板」关键词是固定的吗**？还是租户能自定义？
2. **同行筛选策略**：110,000 个候选，要不要预筛选（资本/年份/官网/英文名/员工规模）？
3. **腾道 + 外贸通同时反推同一同行**，海外买家**分开存档**的精确语义（独立 shared_companies vs 共用 + 多 company_sources）？
4. **腾道时间窗口 2020-至今 + 外贸通时间窗口 2001-至今**：保持差异 vs 统一？
5. **励销云国内联系人**是否抓（手机号为主，归 competitor_contacts）？
