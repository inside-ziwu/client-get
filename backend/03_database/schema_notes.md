<!-- 本文件由人工维护，是 docs/database-schema.md 的「已知漂移与命名注记」章节源文件，
     由 backend/scripts/schema_snapshot.py 渲染时原样拼接到文档尾部。
     结构事实（表/列/约束）不要写在这里——那些由快照自动生成。 -->

## 已知漂移与命名注记

> 本节结论来自 2026-07-22 的生产库实查与全量代码扫描（backend/app、scripts、schema.sql），并与 issue #61/#64 交叉核对。后续注记按同样标准增量维护：只记录有证据的事实，附出处。

### A. 事实源状态

- **迁移链与生产一致**（2026-07-22 核对）：生产 `alembic_version = 20260714_0001` == 仓库迁移链 head（`20260714_0001_drop_retired_collection_tables`）。
- **但空库重放迁移链会失败**（#64）：首个迁移建 `company_scores.tenant_company_id uuid`，与 `tenant_companies.id bigint` 类型冲突。迁移链只能演进存量库，不能作为从零建库的事实源。
- **`schema.sql` 蓝图漂移（不得作为实施依据，.trellis/spec/backend/database-guidelines.md）**：
  - 图有实无 15 张（蓝图声明、生产已不存在）：`clean_companies`、`clean_company_keywords`、`clean_company_sources`、`clean_contacts`、`cleanup_queue`、`collection_keywords`、`collection_runs`、`collection_task_keywords`、`collection_tasks`、`competitor_companies`、`competitor_contacts`、`data_source_credentials`、`data_sources`、`shared_contacts`、`tenant_keyword`；
  - 实有图无 8 张（生产存在、蓝图缺失，全部为外部管道表）：`crawl_progress`、`lixiaoyun_api_clean_companies`、`lixiaoyun_api_companies`、`waimaotong_clean_companies`、`waimaotong_clean_contacts`、`waimaotong_clean_source_links`、`waimaotong_keyword_raw_companies`、`waimaotong_keyword_raw_contacts`。
- **带外列**：`tenant_companies.score_adjustment` 生产存在、代码在用、不在任何迁移（#61 ②）。2026-07-22 核实：#61 提到需排查的 `score_adjusted_at/by/reason` 三列**既不在生产也无任何代码引用**，无报错风险。
- **带外表**：`crawl_progress` 曾被迁移 0054 以「未使用」删除，现存表为外部采集程序**带外重建**（生产约 2.3 万行），仓库代码零读写。
- **带外删除**：`cleanup_queue` 不在生产但仍存在于跑到同版本 head 的开发库（2026-07-22 双库快照对比证实）——它是被生产侧**带外删除**的，迁移链（含 0714）从未删它。
- **备份表清理（2026-07-23，#61 ①）**：原 23 张备份快照表已全部 dump 留档后 DROP（外部书面确认 + 三方依赖核查为零；留档 `~/ClientGet-db-archive/backup-tables-20260723/`，23 个 .sql.gz 逐张行数核验通过，合计 340,596 行）。来源考证（外部确认）：6-02 三批 20 张为外贸通仓库 `repair_clean_company_identity.py` 身份合并保护备份；7-03 两张为本仓库配额事故恢复脚本产物；7-09 一张为外部 AI 标签调整前快照。
- **迁移链编号倒挂**：`20260625_0100_add_instance_id` 的 `down_revision` 指向 `20260701_0002`，实际拓扑为 `…0614_0002 → 0701_0001 → 0701_0002 → 0625_0100 → 0708_0001…`。按文件名排序读迁移史会得出错误顺序，考古时以 `down_revision` 链为准。
- **恒空列**：`waimaotong_clean_companies.email_priority`——2026-07-23 起代码已停止读取（#61 ⑥，后端 4 处+前端 4 处清理），列本身是否删除待外部管道方定夺（对账时已知会）。
- **本文档的视图定义取自生产**（`pg_get_viewdef`），不受 schema.sql 中过时视图定义影响。

### B. DDL 出处全集（建表语句在哪里）

本仓库无 ORM 实体层，schema 定义分布在：

| 位置 | 性质 |
|---|---|
| `backend/alembic/versions/`（70 个迁移） | 唯一正式 schema 演进渠道；镜像启动自动 `upgrade head` |
| `backend/app/db/partitions.py:46-67` | **运行时 DDL**：启动时为 `audit_logs`/`emails`/`intelligence_articles` 自动创建当月+次月分区 |
| `backend/scripts/maintain_partitions.py` | 分区维护脚本（仅覆盖 `emails`/`audit_logs`，与上者逻辑重叠） |
| `backend/scripts/restore_quota_incident_enrollments.py:131,142` | 一次性事故恢复脚本，产出过 `backup_quota_incident_*` 备份表 |
| `backend/03_database/schema.sql` | 手工蓝图，已知漂移（见上），运行时不执行 |

另：`waimaotong_*`、`lixiaoyun_*`、`tendata_*` 等外部直写表的 schema 主权不在本仓库（.trellis/spec/backend/database-guidelines.md），生产中它们的结构变更可能完全不经过本仓库。

**与外部管道方的数据契约约定（2026-07-23 备份表对账时外部书面确认）**：
- `waimaotong_clean_companies` **禁止清空重建**——外部采集口径为增量 upsert/update（其 `clean_waimaotong.py` 有明文），以保护 `tenant_companies.clean_company_id` 等历史关联；
- `waimaotong_keyword_raw_companies`/`waimaotong_keyword_raw_contacts`/`crawl_progress` 为外部在用生产表；双方约定：**任一方新建/重建采集相关表须纳入数据契约并提前知会**（我方侧的探测手段即本快照的 git diff）。

### C. 字段命名与业务含义不一致（DB 列名 ≠ 代码/API 字段名）

**1) SQL `AS` / Python 层显式改名**（DB 列 → 对外字段）：

| 所在表 | DB 列名 | 代码/API 字段名 | 证据 |
|---|---|---|---|
| waimaotong_clean_companies | `product_tags` | `product_keywords` | `tenant_ops_service.py:299` |
| waimaotong_clean_companies | `website` | `company_domain` | `tenant_messaging_service.py:2782,2844,2869,2915` |
| waimaotong_clean_companies | `score` | `wmt_score` | `tenant_query_service.py:388,506` |
| waimaotong_clean_companies | `company_name` / `english_name` | `name` / `name_en` | `tenant_query_service.py:438-439,572-573` |
| waimaotong_clean_companies | `industry` / `employee_size` | `industry_desc` / `employee_num` | `tenant_query_service.py:443,446,578-579` |
| company_scores | `grade` / `total_score` | `system_grade` / `system_score` | `tenant_query_service.py:404-405,544-545` |
| lixiaoyun_api_clean_companies | `entname` | `source_competitor_cn` | `tenant_query_service.py:415,547` |
| tenant_contacts | `contact_status` | `status` | `tenant_ops_service.py:405` |
| sending_plans | `sender_email` / `sender_name` | `from_email` / `from_name` | `tenant_messaging_service.py:1825-1826,1859-1860` |
| sequence_steps | `step_number` | `previous_step` | `tenant_messaging_service.py:2973` |
| intelligence_article_publications | `status` / `created_at` | `publication_status`→`status`、`published_at`→`published_to_tenant_at` | `intelligence_service.py:375,382` |
| ai_models | `display_name` / `is_active` | `model_display_name` / `model_is_active` | `admin_config_service.py:872-873` |

（Pydantic `alias=` 全部用于环境变量/Header/Query 绑定，未发现 DB 列映射。）

**2) 同一业务概念多名并存**：

- 「公司网站/域名」三个名字：`waimaotong_clean_companies.website` 与 `.domain` 双列并存互为兜底（`COALESCE(NULLIF(wc.domain,''), wc.website)`，`tenant_query_service.py:381`），messaging 层再改名 `company_domain`；
- 「国家」双列：`country_iso3` 与 `country` 并存兜底（`tenant_query_service.py:379`），`tenant_ops_service.py:295` 又把 `country_iso3 AS country`；
- raw 层列名（`industry_desc`/`employee_num`）→ clean 层改名（`industry`/`employee_size`）→ API 输出**又改回** raw 层风格，同一字段跨层两套名字。

**3) 误导性命名**：

- `tenant_messaging_service.py` 全篇用别名 `shc` 指代 `waimaotong_clean_contacts`（如 :989,1677,2794），`shc` 实为已退役表 `shared_contacts` 的缩写残留；
- `company_blacklist.shared_company_id` 列名指向已删除的 `shared_companies` 表，实际写入的是清洗层公司 ID 快照（历史遗留命名）；
- `config.py:93` 注释中的 `send_plans.sender_email` 为笔误，实际表名 **`sending_plans`**（全仓库唯一一处误写）；
- 环境变量 `DATA_SOURCE_ENCRYPTION_KEY` 为历史名，现加密的是 `tenant_ai_provider_configs.api_key_encrypted`（OpenRouter Key 等），README §7 已注明不得删除轮换（DB 列名本身无错位）。

### D. 空表（估算行数为 0，可能是未启用/待接线功能）

`ai_usage_logs`、`company_blacklist`、`intelligence_article_publications`、`intelligence_subscriptions`、`notifications`、`scoring_jobs`、`tenant_scoring_weights`（以及备份表中 4 张 scoring 相关快照）。判断是否废弃需结合代码引用频次（见仓库调查记录）。

### E. 设计存在但运行链路未接线的设施（2026-07-22 代码扫描证实的负向事实）

下列结构在 schema 中完整存在，但对应的运行链路**当前不存在**——列说明中已逐一标注，集中列在这里供清理/接线决策参考：

| 设施 | 缺的链路 | 证据要点 |
|---|---|---|
| `scoring_jobs` 队列表（含租约列） | 全库无生产者与消费者，评分已改为同步执行 | 仅租户硬删/迁移清理触达 |
| `service_idempotency_keys` | `InternalIdempotencyService` 已实现 load/save 但无任何调用方 | `request_hash` 无写入路径 |
| `tenant_scoring_weights.weight` | 服务 docstring 声称评分 worker 读取覆盖默认权重，**实际评分引擎未读此表** | 文档与事实不符点 |
| 域名预热自动升降档 | `warmup_rules`/`warmup_rule_levels` 的健康指标列（`min_stay_days`、`min_delivery_rate`、`max_bounce_rate` 等）只有 CRUD，无自动升降档判定；`domain_warmup_status.total_sent`/`bounce_rate` 无回写 | 升降档需人工操作 |
| `domain_daily_usage.sent_count`/`failed_count` | 恒 0，发送侧未回写 | 配额消耗另有口径 |
| `domain_warmup_history.changed_by` | 代码所有 INSERT 均不写，恒 NULL | |
| `emails.scheduled_at` | 全库无代码消费 | 配额事故复盘文档明确；实发口径是 `sent_at IS NOT NULL` |
| `tenant_companies.model_score`/`score` | 只有 SELECT 无写入，评分事实存 `company_scores`；前端「大模型评分」实际绑定 `wmt_score` | 预留列 |
| `groups.auto_rules` | 仅透传存储，无自动分组引擎（`group_members.added_by` 恒写 'manual'） | |
| `contact_rules.rules` | 租户初始化写入默认值，发送侧无任何消费方 | |
| `intelligence_sources.last_fetched_at`/`error_count` | 情报定时采集未实现（#49），无写入方 | |
| `audit_logs.ip_address`/`user_agent`/`request_id`、`ai_usage_logs.latency_ms` | 无填充路径 | 预留 |

**2026-07-23 逐项拍板结果**：
- **接线（已立 issue）**：`tenant_companies.score` 断供（筛选失效 bug）→ #81（P1，回写方案）；域名预热自动升降档三件套 → #82（P2）；审计字段填充 → #83（P3）；
- **拆除**：`service_idempotency_keys` 表 + `InternalIdempotencyService`（零调用方，幂等由 `email_send_locks` 承担；305 行已 dump 留档，迁移 20260723_0003）；
- **保留（预留待接线）**：`scoring_jobs` 队列、`emails.scheduled_at`、`groups.auto_rules`、`contact_rules.rules`（核实修正：发送侧**在用**平台级职位过滤 `v_tenant_contact_classified`，未接线的仅租户自定义规则层）；
- **文档修正**：`tenant_scoring_weights_service.py` docstring 已改正（原声称评分 worker 读取权重，实际未接线）；
- intelligence 定时采集继续由 #49 追踪。
