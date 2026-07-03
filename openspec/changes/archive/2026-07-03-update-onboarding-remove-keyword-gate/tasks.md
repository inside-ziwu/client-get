## 1. 实施

- [x] 1.1 后端 `complete_onboarding` 移除关键词前置校验(点击即置 `needs_onboarding=false`)
- [x] 1.2 租户端 onboarding 按钮文案改为「进入工作台」
- [x] 1.3 新增单元测试:无关键词时 `complete_onboarding` 直接成功且仅执行 UPDATE

## 2. 发布

- [x] 2.1 backend 镜像 r5 起包含,A/B 后端与 Worker 已升级(现 r7)
- [x] 2.2 tenant 镜像已重建部署:B `instanceB-r2`、A `2026.07.03-r1`
- [x] 2.3 生产验证通过:B 租户「刘辉」经引导页进入工作台,并完成建计划与发送
