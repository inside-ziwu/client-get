# 00-06 旧系统文档修复说明

00-06 描述的是“当前已运行的单用户内部工具”。用户已明确新后端从 0 开始写，因此 00-06 不再作为新系统直接实现文档，而作为迁移和复用参考。

## 1. 可复用资产

| 旧系统资产 | 新系统复用方式 |
|---|---|
| FastAPI 路由结构 | 可借鉴，但新系统必须按 Admin/Tenant/Internal/Webhook 分入口。 |
| Prefect Flow 思路 | 可借鉴任务编排，但发送计划不再驱动采集/评分/邮件生成全链路。 |
| 网易外贸通签名/认证逻辑 | 可迁入采集服务 adapter。 |
| OpenRouter 调用封装 | 可迁入 AI service，但必须增加计费、幂等、场景模型配置。 |
| EngageLab 发送封装 | 可迁入 sending service，但必须增加域名、额度、幂等、Webhook。 |
| 邮箱验证工具 | 可复用。 |
| 国家时区/语言映射 | 可复用并集中配置。 |

## 2. 不可直接复用的旧口径

| 旧口径 | 新口径 |
|---|---|
| 单用户 JWT | 多租户 JWT + RLS + RBAC。 |
| `system_config` 明文/混合配置 | 环境变量 + 平台配置表 + AES-256-GCM 加密凭证。 |
| `email_plans` 9 状态 | 采集/评分/发送彻底拆分。 |
| A/B/X 评分 | S/A/B/C/D + 规则为主 + LLM 辅助。 |
| PCB 硬编码 | 行业模板与租户配置。 |
| CORS 全开 | 白名单。 |
| 无审计 | 审计日志。 |
| 无幂等 | 创建、发送、Webhook、Internal API 全部有幂等策略。 |

## 3. 迁移用途

- `01_DATA_MODEL.md` 用于写旧表到新表的迁移脚本。
- `02_API_REFERENCE.md` 用于理解旧前端/旧 API，不作为新 API 合同。
- `03_WORKFLOW_ENGINE.md` 用于拆出采集、评分、AI、发送服务逻辑。
- `04_FRONTEND_MAP.md` 用于对照新 UI/新双应用。
- `05_EXTERNAL_INTEGRATIONS.md` 用于外部适配器实现。
- `06_PRODUCTIZATION_GAP.md` 用于 P0/P1/P2 开发计划。
