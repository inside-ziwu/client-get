# add-root-health-route

## Why

Sealos 探活/负载均衡周期性 GET 根路径 `/`,后端未注册该路由,每次探测都在日志里留下一条 `404 Not Found` 噪音(A/B 两实例均有)。已有 `/health` 路由但探测方不可配置路径。

## What Changes

- 新增 `GET /` 路由,返回 `{"status": "ok"}`(HTTP 200),仅用于探活,不带业务 envelope
- 现有 `/health` 路由保持不变

## Non-Goals

- 不改探测方(Sealos)配置
- 不引入依赖检查型深度健康检查(数据库连通性等)

## Impact

| 范围 | 影响 |
|------|------|
| 后端 | main.py 一个路由 + 一个测试 |
| 部署 | 随下一次 backend 镜像发布,A/B 两实例日志同时去噪 |
