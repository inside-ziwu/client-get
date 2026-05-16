# test-data · 测试材料收件箱

> **目的**：E2E 验收需要"真实测试材料"——用户在这里提供测试租户、测试邮箱、真实采集源、失败场景等。
> **关联**：[`_control/v3/04-v3-e2e-test-plan.md`](../../v3/04-v3-e2e-test-plan.md)
> **安全**：测试材料中**收件邮箱地址**可写明文（用于真实拨测）；**发件邮箱密码 / API 密钥仅注明"已配在 Sealos secret"**，不写明文值。

## 1. 用户该提供什么

按以下模板填写到本目录下 `test-materials.md`（用户新建）：

```markdown
# V3 Test Materials

## 测试租户 A
- 租户 slug：tenant-a-test
- 租户 ID（如已建）：
- 域名：
- 管理员邮箱：a-admin@example.com
- 测试目的：主测试租户，跑 E2E-1 / E2E-2 / E2E-6 等

## 测试租户 B
- 租户 slug：tenant-b-test
- 租户 ID：
- 域名：
- 管理员邮箱：b-admin@example.com
- 测试目的：跑 E2E-4 跨租户隔离

## 发件邮箱（V3-MAIL-001）
- 邮箱地址：sender@yourdomain.com
- 凭证位置：Sealos secret `EMAIL_PROVIDER_API_KEY`（不写明文）
- SMTP 配置：__待补__（host / port，**不**含密码）
- 备注：可发可收，已通过 EngageLab 验证

## 收件邮箱（V3-MAIL-004）
- 收件箱 1：recipient-test1@gmail.com
- 收件箱 2：recipient-test2@example.com
- 备注：用于人工查看是否真实收到邮件

## 真实采集源（V3-COL-002 / 003）
- 关键词列表：
  - "led light wholesale"
  - "garment manufacturer Vietnam"
  - "pet food importer Germany"
- 数据源凭证：__已配在 Sealos secret__（外贸通账号 / 腾道 cookie / 励销云账号）
- 备注：每次跑前先验证账号未失效

## 失败场景配置
- 失败场景 1：错误的邮件配置 → 触发 V3-MAIL-006
- 失败场景 2：无效采集账号 → 触发 V3-COL-003 失败路径
- 失败场景 3：故意触发去重 → V3-COL-006
```

## 2. 字段说明

| 字段 | 是否敏感 | 处置 |
| --- | --- | --- |
| 租户 slug / 域名 / 管理员邮箱 | 低 | 可明文 |
| 测试收件邮箱 | 低 | 可明文（用于真实接收） |
| 发件邮箱地址 | 低 | 可明文 |
| 发件邮箱密码 / API 密钥 | 🔴 高 | **仅注明"已配在 Sealos secret"**，不写值 |
| SMTP host / port | 中 | 可写 |
| 关键词 / 真实采集源 | 低 | 可明文 |
| 数据源账号密码 / cookie | 🔴 高 | 同发件邮箱密码，仅注明位置 |

## 3. 不要在这里做

- ❌ 粘贴密码 / API 密钥 / cookie 真实值
- ❌ 粘贴生产环境的真实租户数据
- ❌ 在文件中保存邮件原文（含敏感内容）

## 4. AI 使用本目录的方式

- E2E 跑前：AI 读 `test-materials.md` 生成测试调用脚本（**只读 key 名 + 引用 secret 位置**，不读 value）
- E2E 跑后：AI 把"是否真实收到邮件"等结果记录到 [`_control/v3/04-v3-e2e-test-plan.md`](../../v3/04-v3-e2e-test-plan.md) 的状态列

## 5. 当前状态

- 文件：占位（用户待建 `test-materials.md`）
- AI 在 Slice 1 / Slice 3 启动前阻塞等待
