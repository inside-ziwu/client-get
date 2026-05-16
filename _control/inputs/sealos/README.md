# sealos · Sealos 应用清单收件箱

> **目的**：用户提供 Sealos 上 7 个（或实际数量）应用的元信息，供 Gap Audit、Release Manifest、E2E 验收使用。
> **绝对原则**：**只填 env key，不填 value**——secrets 不能进 AI 对话或文档。
> **关联**：[`_control/v3/06-v3-release-manifest.md`](../../v3/06-v3-release-manifest.md)、[Gate 10](../../../AGENTS.md#6-门禁规则v3-工作流-10-gates)

## 1. 用户该提供什么

按以下模板填写到本目录下 `applications.md`（用户新建）：

```markdown
# Sealos Applications

## 应用 1：<应用名>

- **服务类型**：admin / backend / collection-worker / sending-worker / collection-scheduler / nginx / 其他
- **镜像地址**：例如 `ghcr.io/xxx/clientget-backend`
- **当前镜像 tag**：例如 `v2.3.1-2026-04-30`
- **端口**：例如 `8000`
- **副本数**：例如 `1`
- **健康检查路径**：例如 `/healthz`
- **关键 env key 列表**（**只列 key 名，禁止粘 value**）：
  - `DATABASE_URL`
  - `JWT_SECRET`
  - `EMAIL_PROVIDER_API_KEY`
  - `OPENROUTER_API_KEY`
  - ...
- **绑定域名**（如有）：例如 `admin.clientget.example.com`
- **备注**：

## 应用 2：...
```

## 2. 字段说明

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| 应用名 | ✅ | Sealos 控制台显示的名称 |
| 服务类型 | ✅ | 用于 Gap Audit 把 Sealos 应用与代码模块对应 |
| 镜像地址 + tag | ✅ | 用于判断当前 Sealos 跑的是哪份代码 |
| 端口 + 副本数 | ✅ | 用于规模与扩展性评估 |
| 健康检查 | ✅ | 用于 Release Manifest §6 验证 |
| env key 列表 | ✅ | 仅 key，**不**含 value |
| 域名 | 选 | 用于前端 E2E 访问入口 |

## 3. 安全规则

- 🔴 **禁止**粘贴 `DATABASE_URL` 的真实值（含密码）
- 🔴 **禁止**粘贴任何 `*_KEY`、`*_SECRET`、`*_TOKEN` 的值
- 🔴 **禁止**粘贴邮箱密码或 SMTP 凭证
- 🟢 ✅ 列出 key 名 / 标注是否已配置（"已配 / 未配"）/ 注明 value 来源（"由 Sealos secret 注入" / ".env 文件"）

如果 AI 在任何阶段读到本目录下出现真实 value，应当：
1. **不复述**该 value
2. 立刻提醒用户从文件中删除
3. 在 [`_control/04-open-questions.md`](../../04-open-questions.md) 登记安全事件

## 4. 当前状态

- 文件：占位（用户待建 `applications.md`）
- AI 在 Gap Audit Step 4 之前阻塞等待此清单

## 5. 用户提供清单后

通知 AI："`_control/inputs/sealos/applications.md` 已就绪，请基于此把 V3 部署目标写到 [`_control/v3/06-v3-release-manifest.md`](../../v3/06-v3-release-manifest.md) §1"
