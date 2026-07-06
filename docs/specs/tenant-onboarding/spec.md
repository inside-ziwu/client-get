# tenant-onboarding Specification

## Purpose

租户新手引导行为规范。来源:归档 change update-onboarding-remove-keyword-gate。

## Requirements

### Requirement: 新手引导 SHALL 可无条件完成

租户管理员点击引导页按钮时,系统 SHALL 直接将租户 `needs_onboarding` 置为 false 并进入工作台,MUST NOT 以关键词、模板、域名等配置完成度作为前置校验。引导页步骤卡片仅作提示。

#### Scenario: 未配置任何关键词也能进入工作台

- **GIVEN** 新建租户,未配置任何采集关键词
- **WHEN** 管理员在引导页点击「进入工作台」
- **THEN** 请求成功,`needs_onboarding` 置为 false,页面跳转工作台,不返回 422

#### Scenario: 按钮文案

- **GIVEN** 租户处于新手引导页
- **WHEN** 页面渲染
- **THEN** 按钮文案为「进入工作台」
