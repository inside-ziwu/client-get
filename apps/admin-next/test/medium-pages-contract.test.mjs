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
  'src/components/ui/sheet.tsx',
  'src/components/ui/alert-dialog.tsx',
  'src/components/ui/select.tsx',
  'src/components/ui/textarea.tsx',
  'src/components/ui/switch.tsx',
  'src/components/ui/checkbox.tsx',
  'src/components/ui/collapsible.tsx',
  'src/components/ui/tabs.tsx',
  'src/app/(dashboard)/intelligence-sources/page.tsx',
  'src/app/(dashboard)/collection/peers/page.tsx',
  'src/app/(dashboard)/collection-tasks/page.tsx',
]) {
  assert.ok(existsSync(resolve(appDir, relativePath)), `缺少 Phase 4 文件：${relativePath}`);
}

const intelligence = read('src/app/(dashboard)/intelligence-sources/page.tsx');
assert.match(intelligence, /adminApi\.intelligenceSources\.list/, '情报源页必须加载列表。');
assert.match(intelligence, /adminApi\.intelligenceSources\.create/, '情报源页必须支持创建。');
assert.match(intelligence, /adminApi\.intelligenceSources\.update/, '情报源页必须支持更新。');
assert.match(intelligence, /adminApi\.intelligenceSources\.delete/, '情报源页必须支持删除。');
assert.match(intelligence, /adminApi\.intelligenceSources\.batchImport/, '情报源页必须支持批量 JSON 导入。');
assert.match(intelligence, /parseJson/, '情报源页必须校验配置 JSON。');
assert.match(intelligence, /formatJson/, '情报源页必须格式化 fetch_config。');
for (const label of ['RSS', '网站', '手工', '最后采集', '批量导入', '填入示例']) {
  assert.match(intelligence, new RegExp(label), `情报源页缺少文案：${label}`);
}

const peers = read('src/app/(dashboard)/collection/peers/page.tsx');
assert.match(peers, /adminApi\.collection\.listRawCompanies\(['"]lixiaoyun['"]/, '同行公司页必须查询励销云 raw 公司。');
assert.match(peers, /PAGE_SIZE\s*=\s*20/, '同行公司页分页大小必须保持 20。');
for (const label of [
  '中文名',
  '英文名',
  '员工规模',
  '注册资金',
  '成立时间',
  '注册地址',
  '网址',
  '联系人',
  '关键词',
  '采集时间',
  '详情',
  '有英文名',
  '有域名',
]) {
  assert.match(peers, new RegExp(label), `同行公司页缺少字段/文案：${label}`);
}
assert.match(peers, /raw_payload/, '同行公司页必须读取 raw_payload。');
assert.match(peers, /safePayload/, '同行公司页必须兼容 raw_payload 为空或非对象，避免线上数据触发白屏。');
assert.match(peers, /contacts/, '同行公司详情必须展示联系人。');
assert.match(peers, /setSelected/, '同行公司页必须支持详情 Sheet 状态。');

const tasks = read('src/app/(dashboard)/collection-tasks/page.tsx');
assert.match(tasks, /adminApi\.collection\.listKeywords/, '采集任务页必须加载关键词。');
assert.match(tasks, /refetchInterval:\s*15_000/, '采集任务页必须保留 15 秒轮询。');
assert.match(tasks, /adminApi\.collection\.trigger/, '采集任务页必须支持触发采集。');
assert.match(tasks, /adminApi\.collection\.listHistory/, '采集任务页必须支持历史记录。');
assert.match(tasks, /API_CHANNEL_BY_ROW/, '采集任务页必须映射展示渠道到 API 渠道。');
assert.match(tasks, /ReverseDetailTable/, '采集任务页必须展示反推阶段详情。');
assert.match(tasks, /resultSummary/, '采集任务历史必须展示结果摘要。');
for (const label of ['直采（外贸通）', '反推（励销云→腾道）', '今日进度', '最近执行', '历史', '重试次数']) {
  assert.match(tasks, new RegExp(label), `采集任务页缺少文案：${label}`);
}
