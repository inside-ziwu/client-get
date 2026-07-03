---
title: Sealos 平台域名(sealosbja.site)下的 cookie 与同站语义
date: 2026-07-03
category: best-practices
module: instance_deployment
problem_type: best_practice
component: authentication
severity: high
applies_when:
  - "用 Sealos 平台分配的 *.sealosbja.site 域名部署前后端"
  - "需要跨子域名携带 httpOnly cookie(如 refresh token)"
tags: [sealos, public-suffix-list, samesite, cookie-domain, cors]
---

# Sealos 平台域名(sealosbja.site)下的 cookie 与同站语义

## Context

Instance B 用 Sealos 自带域名部署(前后端各拿一个随机子域名,如 `aaa.sealosbja.site` / `bbb.sealosbja.site`),需要确认 `SameSite=Lax` 的 refresh cookie 能否跨这两个子域名工作,以及 `COOKIE_DOMAIN` 应该配什么。

## Guidance

核心事实:**`sealosbja.site` 不在 Public Suffix List(PSL)上**(验证方法:`curl -s https://publicsuffix.org/list/public_suffix_list.dat | grep sealos`,无命中)。由此推导出三条规则:

1. **同站判定**:两个随机子域名的可注册域同为 `sealosbja.site`,浏览器视为**同站**——前端到后端的 XHR 是"同站跨源"请求,`SameSite=Lax` cookie 会正常携带,无需 `SameSite=None`;
2. **`COOKIE_DOMAIN` 必须写后端完整主机名**(如 `bbb.sealosbja.site`),**严禁写 `.sealosbja.site`**——由于不在 PSL,浏览器会接受这种超域 cookie,等于把凭证发给该后缀下**所有其他 Sealos 用户的应用**,是真实的凭证泄漏;
3. **CORS 仍然要配**:同站≠同源,后端 `ALLOWED_ORIGINS` 必须显式列出前端完整 origin(https、无尾斜杠),并配合 `allow-credentials: true`。

## Why This Matters

PSL 归属决定了浏览器的同站边界和 cookie 可写域两件事,方向相反:不在 PSL 让 Lax cookie"能用"(好事),同时让超域 cookie"能写"(风险)。不理解这一点,要么把 SameSite 改成 None+额外风险,要么写出泄漏凭证的 Domain。

## When to Apply

- 在任何"平台分配共享后缀域名"的环境(Sealos、Vercel 预览域、Railway 等)配 cookie 时,先查该后缀是否在 PSL——在与不在,cookie 策略完全不同(如 vercel.app 在 PSL,子域名之间是跨站);
- 迁移到独立域名时,`COOKIE_DOMAIN` 改为 `.<新域名>` 形式,同站语义自然恢复。

## Examples

Instance B 实测配置(工作正常):后端 `COOKIE_DOMAIN=sfxteoewmcow.sealosbja.site`;`ALLOWED_ORIGINS=https://zwrvofybyaqa.sealosbja.site,https://ihvjdybutzgy.sealosbja.site`;登录响应 `Set-Cookie: refresh_token=…; Domain=sfxteoewmcow.sealosbja.site; HttpOnly; Secure; SameSite=lax`。

附带风险认知:共享后缀意味着其他 Sealos 用户的应用与你"同站",CSRF 面略宽(响应读取仍被 CORS 拦住,实际可利用性低)——内部起步可接受,正式运营建议换独立域名。
