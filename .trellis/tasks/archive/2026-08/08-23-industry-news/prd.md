# 行业动态（替换遗留情报模块）

> 术语以 [CONTEXT.md](../../../CONTEXT.md)「行业动态」为准；两项结构性决策见 [ADR 0001](../../../docs/adr/0001-industry-news-sources-are-industry-assets.md)（动态源是实例内的行业级资产）与 [ADR 0002](../../../docs/adr/0002-industry-news-is-pure-programmatic-fetching.md)（纯程序化抓取）。本文只写需求、约束与验收，不重复术语与 ADR。需求来源：2026-08-23 grill 三轮 + 两次更正（Q1–Q26），共识已由用户确认。

## Goal

租户用户在产品内看到其所在实例、其行业配置的动态源每日抓取的行业动态——标题 + 原文链接、来源、类别、语种、时间——零 token、零人工维护。首批在 Instance A 接入客户确认的 13 个 PCB 站点；遗留情报模块整体替换。

## 背景与事实

- 客户确认清单：《PCB行业最新动态.docx》13 站，每站带客户自定的「情报类别」。
- 2026-08-21 调研、08-23 复核：13 站全部服务端渲染、普通 HTTP 可取列表；6 站有 RSS，6 行需 HTML 列表规则，2 站列表在 JSON-LD；无站点需要浏览器渲染；姊妹站（PCEA / PCB West / Circuits Assembly）转载率 30–50%。
- 遗留情报模块（`intelligence_*` 四表、按订阅扇出发布、启发式摘要）判定无效：生产 0 文章 / 0 发布 / 0 订阅，仅 2 条历史平台级源。
- 生产 4 个租户行业均为 PCB / 电路板（别名表已有）：Instance A 三个（沐言测试、赵奎、刘辉），Instance B 一个（刘辉）。

## Requirements

### R1 租户端「行业动态」页（`/industry-news`，替换「情报中心」，导航「行业动态」）

- 列表只展示**启用中**动态源的动态（停用即隐藏其全部动态），且抓取时间在 90 天内；页码分页。排序：同一轮抓取的动态在上（一轮内所有动态共用同一抓取时间戳），一轮之内按发布时间倒序（无发布时间的按抓取时间）。
- 每条显示：标题（原文语种，不翻译）、来源（动态源名称）、类别标签、语种标签（英文 / 简体中文 / 繁体中文）、时间（发布时间优先，缺则抓取时间，列头统一「时间」）。
- 外链剪报类来源（PCB Update）：来源显示「PCB Update」，标题后灰字附目标域名。
- 点击标题：新窗口打开原文，并将该条置为当前用户已读；已读与未读颜色明显区分；未读为默认。
- 筛选条：类别（多选）、来源（多选）、语种；「只看未读」开关，默认关；筛选可组合。
- 租户所在实例没有其行业的启用动态源时：导航项照常显示，页面空态提示「本实例尚未配置动态源」。
- 租户内所有角色（含 viewer）可访问。

### R2 管理端「动态源管理」监控页（`/industry-news-sources`，营销分组）

- 源清单完全由仓库种子定义（名称、地址、类别、语种、解析规则，按实例、按行业），页面**只读**展示这些属性。
- 每行：启停开关、上次成功时间、错误计数。页面级「立即抓取」按钮触发本实例一轮抓取。
- 没有新增 / 编辑 / 删除；停用代替删除；新增站点或站点改版是一次开发变更（改种子、发布）。
- 仅平台管理员可启停。
- 本实例没有任何动态源时（如 Instance B），页面空态写明「本实例尚未配置动态源（由开发随种子导入）」，「立即抓取」仍可点但返回"没有可抓取的源"。

### R3 抓取

- 每实例每天北京时间 08:00 一轮，实例级 advisory lock 互斥；仅处理本实例启用的动态源。
- 按源解析规则取标题 + 链接（RSS / HTML 列表选择器 / JSON-LD），不取正文、不翻译、不评分。
- 去重：规范化 URL 或规范化标题任一命中即视为同稿，只保留先抓到的一条。
- 某源失败或解析出 0 条：跳过该源、错误计数 +1、上次成功时间不变；其余源照常；次日例行重试。成功则错误计数归零并更新上次成功时间。
- 不做 RSS 自动发现（Q26 后源完全由种子定义，运营没有加源入口，自动发现没有使用场景；这是对早先口径的有意删除）。
- 入库过滤：带发布时间且发布时间早于 90 天前的条目不入库（防首轮把站点历史灌进"未读"）；无发布时间的条目正常入库。
- 「立即抓取」：一轮进行中再点返回"已在进行"，不排队、不重复。

### R4 数据

- 动态源与动态均带 `instance_id`；动态继承其源的类别与语种；已读按（用户，动态）记录，未读即无记录。
- 90 天窗口按抓取时间计；更早的动态留库不展示，不做物理删除。
- 动态源以稳定代号（`code`，如 `pcea`、`cpca-news`）为身份，种子按 `(instance, code)` 更新，地址可随种子变更。首批种子只导入 Instance A（`instance_id = default`），14 行见下表；Instance B 不导入，种子脚本对非 `default` 实例需显式确认。种子导入生产属写操作，按三段式逐次确认。

### R5 遗留清理

- 删除 `intelligence_sources / intelligence_articles / intelligence_article_publications / intelligence_subscriptions` 四表（含分区）、internal `/intelligence/articles/publish` 端点、租户 `intelligence` 路由、管理端 `intelligence-sources` 端点、两个页面、`shared-api` / `shared-types` 对应类型、相关测试、README 功能矩阵对应行与 `docs/database-schema.md` 对应节。
- 管理端「AI 配置」页隐藏 `intelligence_summary` 场景；PR B 删除 `ai_scene_defaults` 中该场景的默认模型行（否则被它引用的模型永远删不掉），数据库 CHECK 枚举与通知分类枚举 `intelligence` 不动。

## 动态源种子（Instance A · PCB，14 行）

| 名称 | 类别（客户定） | 语种 | 策略 | 地址 | 解析要点（代码内维护） |
|---|---|---|---|---|---|
| PCB Update | PCB 行业新闻 | en | html | `https://pcbupdate.com/` | `td > p > a[href^="http"]`，标题取所在段落全文；只排除自家导航链接（`pcbupdate.com`、`pcea.net/pcb-update-subscription`、`googleapis.com/pcea-digitalmedia`），不得用裸 `pcea` 误杀第三方新闻 |
| PCEA | PCB 技术 / 工程 | en | rss | `https://pcea.net/feed/` | — |
| I-Connect007 | PCB 制造 / 行业新闻 | en | html | `https://iconnect007.com/landing/pcb/news` | `a[href*="/article/"]` |
| PCD&F | PCB 设计 / 工程 | en | rss | `https://pcdandf.com/pcdesign/index.php?format=feed&type=rss` | — |
| Circuits Assembly | PCBA / EMS | en | rss | `https://circuitsassembly.com/ca/editorial/menu-news.feed?type=rss` | — |
| IPC | 行业标准 / 认证 | en | rss | `https://www.electronics.org/rss.xml` | — |
| PCB West | 美国 PCB 展会 | en | rss | `https://pcbwest.com/feed/` | — |
| PCB East | 美国 PCB 展会 | en | rss | `https://pcbeast.com/feed/` | — |
| TPCA | 台湾 PCB 产业 / 展会 | zh-TW | html | `https://www.tpca.org.tw/web/list_news.php?menu_no=312&mod_no=184` | `div.item h2 a` |
| NEPCON JAPAN | 日本电子制造展会 | en | html | `https://www.nepconjapan.jp/hub/en-gb/press.html` | `div.cmp-text p a`，href 匹配 `pressrelease` 或 `.pdf` |
| Productronica | 欧洲电子制造 | en | jsonld | `https://productronica.com/en/trade-fair/press/press-releases/` | ItemList 中 url 含 `/press-releases/detail/`；名称去零宽字符 |
| electronica | 欧洲电子行业 | en | jsonld | `https://electronica.de/en/trade-fair/journalists/press-releases/` | 同上 |
| CPCA 协会动态 | 中国 PCB 行业 | zh-CN | html | `https://www.cpca.org.cn/news.html` | `li.news-item a.lk`，标题 `p.tit` |
| CPCA 每周资讯 | 中国 PCB 行业 | zh-CN | html | `https://www.cpca.org.cn/industry.html` | `div.newspaper-item`，链接 `a.download-btn`，标题 `p.name` |

## Acceptance Criteria

- [x] AC1 Instance A 任一 PCB 租户用户登录后在「行业动态」看到 14 个源的动态，时间倒序、未读高亮；点击打开原文后该条变已读且只对该用户生效。
- [x] AC2 类别 / 来源 / 语种筛选与「只看未读」可组合且结果正确；抓取时间早于 90 天的动态不出现。同稿只归属先抓到的源，按"落选源"筛选看不到该篇，不按 14 源条数对账。
- [~] AC3（去重与 90 天过滤已由首轮证实；08:00 轮次整体置顶待 2026-08-24 观察）08:00 例行抓取后，这一轮新增的动态整体位于列表顶部（一轮内按发布时间倒序）；同稿在多个源出现只显示一条；发布时间早于 90 天前的站点历史条目不入库。
- [x] AC4 管理端显示各源上次成功时间与错误计数；停用的源不再抓取且其动态从租户列表消失；「立即抓取」可触发一轮，进行中再点提示已在进行。错误计数 +1 的路径在开发库用改坏 `parse_config` 的源验证，生产不做破坏性操作。
- [x] AC5 Instance B 租户打开「行业动态」看到空态提示，无报错；Instance B 管理端「动态源管理」空列表带说明。
- [x] AC6 生产无 `intelligence_*` 表、端点、页面残留；`uv run pytest -q`、`pnpm type-check` 通过；去重与 90 天窗口在 Neon 开发库有断言记录。

## Key Decisions（Q1–Q26 决策日志）

| # | 决策 | 结论 |
|---|---|---|
| Q1 | 消费者与入口 | 租户端页面；日报推送、管理端阅读视图不做 |
| Q2 / Q10 / Q23 | 动态源归属 | 实例内的行业级资产；同实例同行业租户自动可见，无租户开关（ADR 0001） |
| Q3 | 呈现主轴 | 单一时间流 + 类别 / 来源 / 语种筛选 |
| Q4 / Q12 / Q20 | 阅读状态 | 仅已读 / 未读，按用户记录，默认未读；「只看未读」默认关 |
| Q5 / Q25 / Q26 | 管理端 | 监控页：只读属性 + 启停 + 健康 + 立即抓取；源的全部属性与解析规则由开发随种子维护 |
| Q6 / Q14 | 保留期 | 只展示最近 90 天（按抓取时间），不物理删除 |
| Q7 | 术语 | 行业动态 / 动态 / 动态源 / 类别 / 语种 / 同稿 / 抓取（CONTEXT.md） |
| Q8 | 抓取节奏 | 每天北京时间 08:00 一轮 + 立即抓取按钮 |
| Q9 | 入口 | 导航「行业动态」替换情报中心；无仪表盘卡片、无角标 |
| Q11 / Q18 / Q23 | 实例范围 | 动态源与动态带 `instance_id`，每实例各自抓取；首批只配 Instance A |
| Q13 | 字段与交互 | 见 R1 |
| Q15 / Q19 | 健康与失败 | 被动显示上次成功时间与错误计数；失败或 0 条计数 +1、跳过本轮、次日重试；不标红、不自动停用、不外发告警 |
| Q16 / Q21 | 遗留处置 | 全删新建；AI 场景只在管理端隐藏 |
| Q17 | ADR | 记 0001、0002（0003 因 Q23 更正撤销） |
| Q22 | 命名 | 路由改为 `/industry-news`、`/industry-news-sources` |
| Q24 | 无源租户 | 导航照常，页面空态提示 |
| 前置 | 抓取内容 | 只取标题 + 链接；不翻译、零 token；13 站一批全接（ADR 0002） |

## Out of Scope

正文抓取、翻译、摘要 / 相关度评分；仪表盘卡片与未读角标；站内通知 / 日报推送；人工审核、隐藏单条、手工补录；租户级开关或私有源；管理端新增 / 编辑 / 删除源；自动停用与外发告警；物理删除旧动态；跨实例共享；浏览器渲染或外部抓取服务；Instance B 的源配置。

## Risks / Deferred

- 站点改版导致某源 0 条：只能靠管理端错误计数被运营发现，修复是开发变更。
- PCB Update 标题取段落全文的规则需在 dry-run 时按样本微调；NEPCON 含 PDF 链接（直接作为原文链接）；慕尼黑两站标题含零宽字符需清洗。
- 姊妹站去重依赖规范化标题，标题微调的同稿会漏判为两条（可接受）。
- 生产种子导入为写操作，执行前展示 14 行并取得确认。
- 延后项：日报推送、仪表盘卡片、租户私有源、外发告警、Instance B 配置。

## Notes（产物状态）

- `prd.md`：✅ 本文件（2026-08-23，用户已确认共识）。
- `CONTEXT.md`、`docs/adr/0001`、`docs/adr/0002`：✅ 已落盘（待提交）。
- `design.md`（数据模型、抓取模块、API、页面结构、迁移与种子脚本）与 `implement.md`（执行顺序、验证命令、回滚点）：规划阶段下一步产出，产出并经用户批准后才 `task.py start`。
