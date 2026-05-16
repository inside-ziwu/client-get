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
  'src/app/(dashboard)/warmup-rules/page.tsx',
  'src/app/(dashboard)/ai-config/page.tsx',
]) {
  assert.ok(existsSync(resolve(appDir, relativePath)), `缺少页面：${relativePath}`);
}

const warmup = read('src/app/(dashboard)/warmup-rules/client-page.tsx');
assert.match(warmup, /adminApi\.warmupRules\.get/, 'WarmupRules 必须加载后端预热规则。');
assert.match(warmup, /adminApi\.warmupRules\.update/, 'WarmupRules 必须保存到后端。');
assert.match(warmup, /min_observation_emails/, 'WarmupRules 必须保留高级参数 min_observation_emails。');
assert.match(warmup, /bounce_alert_rate/, 'WarmupRules 必须保留退信报警阈值。');
for (const field of [
  'daily_limit',
  'min_stay_days',
  'min_delivery_rate',
  'max_bounce_rate',
  'max_complaint_rate',
]) {
  assert.match(warmup, new RegExp(field), `WarmupRules 缺少档位字段：${field}`);
}
assert.match(warmup, /addLevel/, 'WarmupRules 必须支持新增档位。');
assert.match(warmup, /removeLevel/, 'WarmupRules 必须支持删除档位。');

const ai = read('src/app/(dashboard)/ai-config/client-page.tsx');
assert.match(ai, /adminApi\.aiConfig\.getPricing/, 'AIConfig 必须加载模型和场景默认值。');
assert.match(ai, /adminApi\.aiConfig\.createModel/, 'AIConfig 必须支持创建模型。');
assert.match(ai, /adminApi\.aiConfig\.updateModel/, 'AIConfig 必须支持更新模型。');
assert.match(ai, /adminApi\.aiConfig\.deleteModel/, 'AIConfig 必须支持删除模型。');
assert.match(ai, /adminApi\.aiConfig\.updateSceneDefaults/, 'AIConfig 必须支持更新场景默认模型。');
for (const label of ['客户评分', '邮件生成', '情报摘要', '数据分析', '通用']) {
  assert.match(ai, new RegExp(label), `AIConfig 缺少场景文案：${label}`);
}
assert.match(ai, /display_name/, 'AIConfig 必须保留显示名称字段。');
assert.match(ai, /provider/, 'AIConfig 必须保留 provider 字段。');
assert.match(ai, /model_id/, 'AIConfig 必须保留 model_id 字段。');
assert.match(ai, /is_active/, 'AIConfig 必须保留启用状态字段。');
