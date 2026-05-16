# OpenSpec · 项目上下文

> 该文件被 OpenSpec skill 读取，作为生成 proposal / design / tasks 时的项目背景。

## 项目简介

ClientGet：B2B 外贸客户智能平台。工作区结构与代码主入口见根目录 [AGENTS.md](../AGENTS.md) 与 [_control/01-code-roots.md](../_control/01-code-roots.md)。

## 技术栈

- 前端：pnpm monorepo（Tenant + Admin），<!-- TODO 框架 -->
- 后端：<!-- TODO -->
- 数据库：<!-- TODO -->
- 部署：Sealos

## 约定

- 中文沟通、中文注释、中文提交信息
- 简洁优先（KISS），避免过度防御性设计
- 任何变更前先读 `_control/` 控制区
- 不移动 `docs/` 与 `blueprint/` 下文件

## 当前活跃 change

- `changes/v3-complete-collection-email/` — v3 主线（占位，待用户确认范围）
