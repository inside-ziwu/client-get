# update-onboarding-remove-keyword-gate

## Why

租户新手引导的「完成并进入工作台」按钮要求租户已配置至少一个有效采集关键词(后端 422),但引导页三张步骤卡片均为纯展示、无任何配置入口,新租户(如 Instance B 首个租户)会卡死在引导页且前端只显示笼统的"提交失败"。产品决策(2026-07-03 用户确认):引导页仅作提示,不设进入门槛。

## What Changes

- 后端 `complete_onboarding` 移除关键词数量前置校验,点击即标记 `needs_onboarding=false`
- 租户端按钮文案「完成并进入工作台」改为「进入工作台」
- 引导三步骤保留为提示性内容,不做完成度校验

## Non-Goals

- 不给引导页增加配置入口或完成度打勾(后续再议)
- 不改登录后的引导跳转逻辑

## Impact

| 范围 | 影响 |
|------|------|
| 后端 | `tenant_settings_service.complete_onboarding` 移除校验 |
| 租户前端 | onboarding 页按钮文案 |
| 部署 | 需重建 backend 镜像与 tenant 前端镜像(A/B 通用行为变更) |
