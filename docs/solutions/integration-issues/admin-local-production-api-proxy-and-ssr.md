---
title: 本地 Admin 对接生产实例时必须同时配置浏览器代理与 SSR 后端地址
date: 2026-07-15
category: integration-issues
module: admin_frontend
problem_type: local_production_integration
component: nextjs_admin
severity: medium
applies_when:
  - "使用本地 Admin 页面只读验收生产实例"
  - "登录成功后 SSR 页面仍请求 localhost:8000"
tags: [nextjs, admin, ssr, cors, local-proxy, production-api]
---

# 本地 Admin 对接生产实例时必须同时配置浏览器代理与 SSR 后端地址

## 现象

直接把 `NEXT_PUBLIC_ADMIN_API_BASE_URL` 指向生产 API 时，登录请求会被生产 CORS 拒绝；只配置 Next.js rewrite 时，浏览器登录虽然成功，`server-api.ts` 的 SSR 预取仍会回退到 `http://localhost:8000`，页面控制台出现 `[SSR] ... fetch failed`。

## 原因

Admin 有两条独立数据链路：

1. 浏览器端 `@shared/api` 读取 `NEXT_PUBLIC_ADMIN_API_BASE_URL`；
2. 服务端预取读取 `BACKEND_INTERNAL_URL`。

本地浏览器直连生产域名还会携带 `Origin: http://localhost:<port>`，生产 CORS 不允许该来源。Next.js rewrite 可以提供同源入口，但不能替代 SSR 的后端地址。

## 正确启动方式

仅用于用户明确授权的生产只读/视觉验收，不写入 `.env`：

```bash
NEXT_PUBLIC_ADMIN_API_BASE_URL= \
ADMIN_API_REWRITE_TARGET=https://api.xinanpcb.com \
BACKEND_INTERNAL_URL=https://api.xinanpcb.com \
pnpm exec next dev -p 3002
```

- `NEXT_PUBLIC_ADMIN_API_BASE_URL=`：浏览器使用当前站点的相对路径；
- `ADMIN_API_REWRITE_TARGET`：开发服务器把 `/admin/api/*` 同源转发到目标实例；
- `BACKEND_INTERNAL_URL`：SSR 直接请求同一目标实例。

## 验证

登录后访问任一 SSR 列表页，开发日志应出现目标生产域名，例如：

```text
[SSR] ✓ https://api.xinanpcb.com/admin/api/v1/intelligence-sources
```

若日志仍出现 `localhost:8000`，说明漏配 `BACKEND_INTERNAL_URL`。真实生产状态切换、创建、删除等写操作仍需单独授权；视觉 Gate 只打开、取消和查询。
