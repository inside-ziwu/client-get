import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const appDir = resolve(__dirname, '..');

function read(relativePath) {
  return readFileSync(resolve(appDir, relativePath), 'utf8');
}

for (const relativePath of [
  'src/app/(dashboard)/data-sources/page.tsx',
  'src/app/(dashboard)/contact-classification/page.tsx',
  'src/app/(dashboard)/email-templates/page.tsx',
  'src/components/grapes-email-editor.tsx',
  'src/components/ui/calendar.tsx',
  'src/components/ui/date-picker.tsx',
  'src/app/(dashboard)/collection/tendata/page.tsx',
  'src/app/(dashboard)/collection/customers/page.tsx',
  'src/app/(dashboard)/collection/peers-cleaned/page.tsx',
  'src/app/(dashboard)/scoring-templates/page.tsx',
  'src/app/(dashboard)/tenants/page.tsx',
]) {
  assert.ok(existsSync(resolve(appDir, relativePath)), `缺少 Phase 4/5 文件：${relativePath}`);
}

const dataSources = read('src/app/(dashboard)/data-sources/client-page.tsx');
assert.match(dataSources, /adminApi\.dataSources\.list/, '数据源页必须加载数据源列表。');
assert.match(dataSources, /adminApi\.dataSources\.create/, '数据源页必须支持创建数据源。');
assert.match(dataSources, /adminApi\.dataSources\.update/, '数据源页必须支持更新数据源。');
assert.match(dataSources, /adminApi\.dataSources\.patchConfig/, '数据源页必须支持单独保存配置。');
assert.match(dataSources, /adminApi\.dataSources\.getCredentials/, '数据源页必须加载凭证列表。');
assert.match(dataSources, /adminApi\.dataSources\.createCredential/, '数据源页必须支持创建凭证。');
assert.match(dataSources, /adminApi\.dataSources\.updateCredential/, '数据源页必须支持更新凭证。');
assert.match(dataSources, /adminApi\.dataSources\.deleteCredential/, '数据源页必须支持删除凭证。');
assert.match(dataSources, /CREDENTIAL_FIELDS_BY_TYPE/, '数据源页必须保留按来源类型变化的凭证字段。');
assert.match(dataSources, /parseJson/, '数据源页必须校验 JSON 配置。');
for (const label of ['外贸通', '腾道', '励销云', '凭证', '账号编号', '每日额度', '轮换顺序', '配置 JSON']) {
  assert.match(dataSources, new RegExp(label), `数据源页缺少字段/文案：${label}`);
}

const classification = read('src/app/(dashboard)/contact-classification/client-page.tsx');
assert.match(classification, /adminApi\.contactClassification\.listLevels/, '联系人分类页必须加载层级。');
assert.match(classification, /adminApi\.contactClassification\.createLevel/, '联系人分类页必须支持创建 Level。');
assert.match(classification, /adminApi\.contactClassification\.updateLevel/, '联系人分类页必须支持更新 Level。');
assert.match(classification, /adminApi\.contactClassification\.deleteLevel/, '联系人分类页必须支持删除 Level。');
assert.match(classification, /adminApi\.contactClassification\.createCategory/, '联系人分类页必须支持创建 Category。');
assert.match(classification, /adminApi\.contactClassification\.deleteCategory/, '联系人分类页必须支持删除 Category。');
assert.match(classification, /adminApi\.contactClassification\.addKeywords/, '联系人分类页必须支持批量添加关键词。');
assert.match(classification, /adminApi\.contactClassification\.deleteKeyword/, '联系人分类页必须支持删除关键词。');
assert.match(classification, /is_sendable/, '联系人分类页必须保留可发送开关。');
for (const label of ['Level', 'Category', 'Keywords', '批量关键词', '可发送', '关键词一行一个']) {
  assert.match(classification, new RegExp(label), `联系人分类页缺少字段/文案：${label}`);
}

const editor = read('src/components/grapes-email-editor.tsx');
assert.match(editor, /forwardRef/, 'GrapesJS 编辑器必须使用 forwardRef。');
assert.match(editor, /useImperativeHandle/, 'GrapesJS 编辑器必须暴露 imperative handle。');
assert.match(editor, /grapesjs/, 'GrapesJS 编辑器必须加载 grapesjs。');
assert.match(editor, /grapesjs-preset-newsletter/, 'GrapesJS 编辑器必须加载 newsletter preset。');
assert.match(editor, /getHtml/, 'GrapesJS 编辑器必须支持读取 HTML。');
assert.match(editor, /getDesign/, 'GrapesJS 编辑器必须支持读取 design。');

const emails = read('src/app/(dashboard)/email-templates/client-page.tsx');
assert.match(emails, /adminApi\.emailTemplates\.list/, '邮件模板页必须加载模板列表。');
assert.match(emails, /adminApi\.emailTemplates\.detail/, '邮件模板页必须加载模板详情。');
assert.match(emails, /adminApi\.emailTemplates\.create/, '邮件模板页必须支持创建模板。');
assert.match(emails, /adminApi\.emailTemplates\.update/, '邮件模板页必须支持更新模板。');
assert.match(emails, /adminApi\.emailTemplates\.delete/, '邮件模板页必须支持删除模板。');
assert.match(emails, /GrapesEmailEditor/, '邮件模板页必须集成 GrapesJS 编辑器。');
assert.match(emails, /body_html/, '邮件模板页必须保存 body_html。');
assert.match(emails, /body_design/, '邮件模板页必须保存 body_design。');
for (const label of ['变量', 'HTML 模式', '可视化模式', '预览', '行业', '主题']) {
  assert.match(emails, new RegExp(label), `邮件模板页缺少字段/文案：${label}`);
}

const calendar = read('src/components/ui/calendar.tsx');
const datePicker = read('src/components/ui/date-picker.tsx');
assert.match(calendar, /DayPicker/, 'Calendar 组件必须基于 react-day-picker。');
assert.match(datePicker, /Calendar/, 'DatePicker 必须复用 Calendar。');
assert.match(datePicker, /formatDate/, 'DatePicker 必须格式化日期显示。');

const tendata = read('src/app/(dashboard)/collection/tendata/client-page.tsx');
assert.match(tendata, /adminApi\.collection\.listRawCompanies\(['"]tendata['"]/, 'Tendata 页必须查询 tendata raw 公司。');
assert.match(tendata, /DatePicker/, 'Tendata 页必须使用日期选择器。');
assert.match(tendata, /RangeField/, 'Tendata 页必须保留范围筛选字段。');
assert.match(tendata, /contactsFrom/, 'Tendata 详情必须展示联系人。');
for (const label of ['Tendata 采集归档', '贸易金额', '供应商', '成立年份', '国家', '联系人', '详情']) {
  assert.match(tendata, new RegExp(label), `Tendata 页缺少字段/文案：${label}`);
}

const customers = read('src/app/(dashboard)/collection/customers/client-page.tsx');
assert.match(customers, /adminApi\.collection\.listCleanCompanies/, '客户归档页必须查询 clean companies。');
assert.match(customers, /adminApi\.collection\.getCleanupHealth/, '客户归档页必须展示清洗健康状态。');
assert.match(customers, /RangeField/, '客户归档页必须保留范围筛选字段。');
assert.match(customers, /Sheet/, '客户归档页必须提供详情 Sheet。');
for (const label of ['客户采集归档', '规范化公司', '来源', '待清洗', '失败耗尽', '处理速度', '详情']) {
  assert.match(customers, new RegExp(label), `客户归档页缺少字段/文案：${label}`);
}

const peersCleaned = read('src/app/(dashboard)/collection/peers-cleaned/client-page.tsx');
assert.match(peersCleaned, /adminApi\.collection\.listPeerCompanies/, '同行数据清洗页必须查询 peer companies API。');
assert.match(peersCleaned, /adminApi\.collection\.getPeerCompanyHealth/, '同行数据清洗页必须展示 peer company health 指标。');
assert.doesNotMatch(peersCleaned, /listRawCompanies|collection\/raw\/lixiaoyun/, '同行数据清洗页不能查询原 raw 同行公司 API。');
assert.match(peersCleaned, /row\.keywords\.slice\(0,\s*3\)/, '同行数据清洗页关键词数组需要折叠展示。');
assert.match(peersCleaned, /Sheet/, '同行数据清洗页必须提供详情 Sheet。');
for (const label of ['同行数据（清洗）', 'Raw 数', 'Peer 数', '去重率', '英文名覆盖率', '是否有英文名', '关键词数', '励销云 source_id']) {
  assert.match(peersCleaned, new RegExp(label), `同行数据清洗页缺少字段/文案：${label}`);
}

const scoring = read('src/app/(dashboard)/scoring-templates/client-page.tsx');
assert.match(scoring, /adminApi\.scoringTemplates\.list/, '评分模板页必须加载列表。');
assert.match(scoring, /adminApi\.scoringTemplates\.detail/, '评分模板页必须加载详情。');
assert.match(scoring, /adminApi\.scoringTemplates\.create/, '评分模板页必须支持创建。');
assert.match(scoring, /adminApi\.scoringTemplates\.update/, '评分模板页必须支持更新。');
assert.match(scoring, /adminApi\.scoringTemplates\.delete/, '评分模板页必须支持删除。');
assert.match(scoring, /DimensionEditor/, '评分模板页必须包含 DimensionEditor。');
assert.match(scoring, /grade_thresholds/, '评分模板页必须支持等级阈值。');
assert.match(scoring, /normalizeDimensions/, '评分模板页必须兼容旧格式 dimensions。');
for (const label of ['评分维度', '等级阈值', 'S 级', 'A 级', 'B 级', 'C 级', 'D 级', '预览']) {
  assert.match(scoring, new RegExp(label), `评分模板页缺少字段/文案：${label}`);
}

const tenants = read('src/app/(dashboard)/tenants/client-page.tsx');
assert.match(tenants, /adminApi\.tenants\.list/, '租户页必须加载租户列表。');
assert.match(tenants, /adminApi\.tenants\.create/, '租户页必须支持创建租户。');
assert.match(tenants, /adminApi\.tenants\.update/, '用户详情必须支持编辑保存基础信息。');
assert.match(tenants, /adminApi\.tenants\.suspend/, '租户页必须支持暂停租户。');
assert.match(tenants, /adminApi\.tenants\.activate/, '租户页必须支持启用租户。');
assert.match(tenants, /adminApi\.tenants\.delete/, '租户页必须支持删除租户。');
assert.match(tenants, /adminApi\.tenants\.listDomains/, '租户页必须加载域名。');
assert.match(tenants, /adminApi\.tenants\.createDomain/, '租户页必须支持添加域名。');
assert.match(tenants, /adminApi\.tenants\.verifyDomain/, '租户页必须支持验证域名。');
assert.match(tenants, /adminApi\.tenants\.listTeam/, '租户页必须加载团队。');
assert.match(tenants, /adminApi\.tenants\.createTeamUser/, '租户页必须支持创建成员。');
assert.match(tenants, /adminApi\.tenants\.updateTeamUser/, '租户页必须支持更新成员。');
assert.match(tenants, /adminApi\.tenants\.deleteTeamUser/, '租户页必须支持删除成员。');
assert.match(tenants, /adminApi\.tenants\.getOpenRouter/, '租户页必须读取 OpenRouter 配置。');
assert.match(tenants, /adminApi\.tenants\.updateOpenRouter/, '租户页必须保存 OpenRouter 配置。');
assert.match(tenants, /adminApi\.tenants\.refreshOpenRouterBalance/, '租户页必须刷新 OpenRouter 余额。');
assert.match(tenants, /adminApi\.warmupRules\.get/, '域名添加必须从预热规则配置读取可选档位。');
assert.match(tenants, /navigator\.clipboard\.writeText/, '用户详情必须支持复制后台管理地址。');
assert.match(tenants, /getTenantAdminUrl/, '用户详情必须生成后台管理地址。');
assert.match(tenants, /Tabs/, '用户详情必须使用 Tabs。');
for (const label of ['用户管理', '基础信息', '后台管理地址', '复制', '域名', '预热档位', '团队', 'OpenRouter', '暂停', '启用', '验证域名', '已验证', '刷新余额']) {
  assert.match(tenants, new RegExp(label), `用户页缺少字段/文案：${label}`);
}
assert.doesNotMatch(tenants, /租户/, 'Admin 用户管理页展示文案不应再出现「租户」。');
for (const field of ['admin_email', 'admin_name', 'admin_password']) {
  assert.match(tenants, new RegExp(field), `用户创建表单必须提交后端必填字段：${field}`);
}
assert.doesNotMatch(tenants, /tenantForm\.slug|name:\s*'slug'|Label>发件域名|Label>起始预热档位/, '创建用户表单不应要求手动填写 Slug、发件域名或预热档位。');
assert.doesNotMatch(tenants, /sender_domain:\s*tenantForm|warmup_level:\s*tenantForm/, '创建用户 payload 不应从创建表单提交发件域名或预热档位。');
assert.match(tenants, /createDomain\(selected\.id,\s*\{\s*domain:\s*domainText\.trim\(\),\s*warmup_rule_id:/s, '添加域名必须提交预热规则 ID。');
assert.match(tenants, /warmup_level:\s*Number\(domainWarmupLevel\)/, '添加域名必须提交所选预热档位。');
