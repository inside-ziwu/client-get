## 1. 实施

- [x] 1.1 后端 `complete_onboarding` 移除关键词前置校验(点击即置 `needs_onboarding=false`)
- [x] 1.2 租户端 onboarding 按钮文案改为「进入工作台」
- [x] 1.3 新增单元测试:无关键词时 `complete_onboarding` 直接成功且仅执行 UPDATE

## 2. 发布

- [ ] 2.1 重建 backend 镜像并更新 A/B 后端与 Worker(行为对两实例统一生效)
- [ ] 2.2 重建 tenant 前端镜像(B 用 api_url 注入;A 随下次常规构建)
- [ ] 2.3 B 租户「刘辉」引导页点击「进入工作台」验证通过
