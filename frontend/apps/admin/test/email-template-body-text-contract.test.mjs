import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const appDir = resolve(__dirname, '..');

const emails = readFileSync(
  resolve(appDir, 'src/app/(dashboard)/email-templates/client-page.tsx'),
  'utf8',
);

assert.match(emails, /const \[bodyText,\s*setBodyText\] = useState\(''\)/, 'Admin 邮件模板页必须保存编辑器输出的 bodyText 状态。');
assert.match(emails, /setBodyText\(text\)/, 'Admin 邮件模板页必须接收富文本编辑器输出的纯文本。');
assert.match(emails, /body_text:\s*bodyText/, 'Admin 邮件模板 create/update payload 必须提交 body_text。');
assert.match(emails, /body_design:\s*null/, 'Admin 邮件模板保存必须继续清空 body_design。');
