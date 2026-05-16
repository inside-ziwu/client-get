## Context

租户端公司列表页已有“新建公司”入口，前端把表单值提交到 `POST /api/v1/companies`，后端由 `TenantOpsService.create_company` 写入 `clean_companies` 与 `tenant_companies`。当前实现已接近 V3 状态语义：手工创建后应为 `business_status = new`、`visibility_status = visible`，并使用数据库自增的 tenant company identity。

保存时报错已通过本地 service 级调用复现出两个确定失败点：

- 前端新建公司表单的国家输入框提示 `DE / US / JP`，用户按提示填写 ISO2 时，后端当前逻辑把 `country` 前三位或原值大写后写入 `clean_companies.country_iso3`。本地数据库约束 `clean_companies_country_iso3_check` 要求 `country_iso3 IS NULL OR country_iso3 ~ '^[A-Z]{3}$'`，因此 `US`、`DE`、`CN` 会触发 `CheckViolationError`；`USA`、`DEU`、`CHN` 会通过；英文长名如 `United States` 会被截为 `UNI`，虽然通过约束但语义错误。
- 填写联系人邮箱时，`TenantOpsService.create_company` 将 `RETURNING id` 得到的 bigint tenant company id 转成字符串，再传给 `_ensure_contact_from_payload`。该 helper 查询 `SELECT clean_company_id FROM tenant_companies WHERE id = :tenant_company_id` 时没有 cast，asyncpg 按 bigint 参数收到字符串，例如 `'692'`，触发 `DataError: 'str' object cannot be interpreted as an integer`。

已有证据还显示：不填写联系人、国家为空时当前逻辑会写入 `UNK` 并保存成功；不填写联系人、国家为 `USA` 时重复创建同一公司会返回同一个 tenant company id，现有幂等行为可保留。

## Goals / Non-Goals

**Goals:**

- 修复租户端新建公司保存失败，确保使用前端表单可选国家和联系人邮箱时也可以创建或关联公司并返回当前 V3 tenant company。
- 将新建公司国家输入收口为 ISO3 机器键，避免 ISO2、英文长名或未知值直接写入 `country_iso3`。
- 修复联系人补写中的 tenant company id 类型不匹配。
- 保持现有 V3 语义：`business_status = new`，`visibility_status = visible`，`data_status` 仅表达数据可用性。
- 让前端展示后端返回的明确错误信息，并在成功后刷新公司列表。
- 用后端测试和前端测试覆盖 ISO2/ISO3 国家输入、联系人邮箱、重复创建或已有公司关联场景。

**Non-Goals:**

- 不重做公司管理页面 UI。
- 不引入新的公司状态、评分语义或黑名单语义。
- 不改变采集、fan-out、评分或发送链路。
- 不做生产数据库同步、镜像推送或上线操作。

## Decisions

1. **国家值优先在前端选择，后端做最小兜底**

   新建公司表单的国家字段应复用已有 `countryOptionsZh()`，让用户看到中文国家名，提交值保持 ISO3，例如 `美国 -> USA`。这与客户列表/筛选已经采用的国家展示规则一致，也避免继续提示 `DE / US / JP` 诱导 ISO2 输入。

   后端仍需在写入 `clean_companies.country_iso3` 前做最小规范化/校验：接受空值并沿用现有 `UNK` 兜底；接受三位大写 ISO3；对于 ISO2 输入，优先使用后端已有依赖 `pycountry` 转换为 ISO3，至少覆盖前端旧提示样本 `US`、`DE`、`CN`、`JP`；无法可靠识别的值返回明确校验错误，不再截取前三位。前端国家选项继续由 `countryOptionsZh()` 提供，后端不复制前端中文映射表，只负责机器码标准化。

   备选方案是只改前端控件；这不能保护 batch import 或直接 API 调用。只改后端也能止血，但会保留错误的 UI 提示和自由输入体验。

2. **联系人补写保持现有模型，只修正 id 类型边界**

   `create_company` 返回给 API 的 `id` 可以继续是字符串，但传入 `_ensure_contact_from_payload` 的内部 tenant company id 必须保持 bigint/int，或 helper 查询必须显式 cast。优先保持内部 id 类型正确，避免在每个 SQL 查询点重复 cast。

   备选方案是在 `_ensure_contact_from_payload` 查询中改为 `CAST(CAST(:tenant_company_id AS text) AS bigint)`；这能修复症状，但会延续“内部 bigint id 先转字符串再传回 SQL”的混乱边界。

3. **保存逻辑保持两段式：clean company upsert + tenant company create/link**

   `clean_companies` 继续按规范化公司名和国家维度 upsert，`tenant_companies` 继续按 `(tenant_id, clean_company_id)` 去重。重复创建时返回已存在的 tenant company，避免唯一约束错误直接暴露给用户。

   备选方案是前端先查重再创建；这会增加竞态，不能替代后端幂等保护。

4. **状态字段只写当前 V3 合法值**

   新建公司只写 `business_status = new`、`visibility_status = visible`，`data_status` 从资料和联系人可用性推导为 `ready`、`missing_contacts` 或 `insufficient_data`。不得写入 legacy `selected`、`pending_score`、`scored`，也不得手动插入 UUID 到 bigint identity。

5. **请求 schema 是可选收紧项，不作为本次根因前置假设**

   后端 API 直接收 `dict`、前端 shared API 使用 `Record<string, unknown>` 仍是契约风险，但不是已复现的直接根因。实施时可以顺手新增轻量 typed request / Pydantic schema，但必须服务于上述两个根因修复，不能把本 change 扩成完整 API 契约重构。

6. **前端错误展示跟随后端 message**

   页面提交前做 trim 和空值剔除；保存失败时优先展示后端业务错误信息，避免统一显示“公司创建失败”导致无法定位。

## Risks / Trade-offs

- **ISO2 转 ISO3 覆盖不足** → 后端优先使用 `pycountry` 的 ISO2/ISO3 标准映射，测试至少覆盖前端旧提示样本 `US`、`DE`、`JP` 以及当前复现过的 `CN`；未知值明确报错，不猜测。
- **`UNK` 是否继续用于空国家** → 为保持现有保存能力，本 change 保留空国家写 `UNK` 的行为；若后续要改为 `NULL` 或强制必填，另开 change。
- **新增 schema 可能影响 batch import 复用 create_company 的方式** → 本 change 不强制做 schema 重构；如新增 schema，需要确认 batch import 兼容并覆盖测试。
- **前端错误解析依赖 Axios 响应形状** → 复用项目现有错误处理模式，避免引入全局拦截器改动。

## Migration Plan

预计不需要数据库迁移。若实施排查确认当前数据库缺少 V3 字段、约束或函数导致保存失败，必须先更新本 change 的 design/tasks，补充 Alembic 迁移、回滚方式和验证命令后再实施。

部署仅需随 backend / tenant frontend 正常发布。正式镜像推送、生产迁移、线上重启必须由用户明确触发。

## Open Questions

- 无需用户决策。当前按已复现证据实施：国家 ISO2/ISO3 标准化和联系人补写 id 类型修复。
