---
title: EngageLab API 持续 401(code 30000)——账户数据中心与 base_url 不匹配
date: 2026-07-03
category: integration-issues
module: email_sending
problem_type: integration_issue
component: email_processing
symptoms:
  - "调用 EngageLab REST API 返回 HTTP 401 {\"code\": 30000, \"message\": \"Authentication failed\"}"
  - "API_USER 与 API KEY 反复核对、轮换后仍然 401"
  - "同账户的 webhook 推送正常(绿点可用),唯独主动调用被拒"
root_cause: config_error
resolution_type: config_change
severity: high
tags: [engagelab, 401, datacenter, base-url, basic-auth]
---

# EngageLab API 持续 401(code 30000)——账户数据中心与 base_url 不匹配

## Problem

Instance B 的 EngageLab 凭证无论怎么核对、轮换,调用发送/查询 API 一律返回 401 Authentication failed(code 30000),邮件发送持续失败。

## Symptoms

- `POST /v1/mail/send`、`GET /v1/email_status` 均返回 `401 {"code":30000,"message":"Authentication failed"}`
- 重置 API KEY 后依然 401
- 同一账户在 EngageLab 后台配置的 webhook 回调正常工作(方向相反,不走同一认证)

## What Didn't Work

- 反复核对/轮换 API_USER 的 API KEY——值本身是对的
- 检查 key 类型(API KEY vs APP KEY)、复制杂质、API_USER 全名——均无问题
- 怀疑批量/触发型 API_USER 权限差异——被 Instance A(同为批量型,正常发送)证伪

## Solution

**EngageLab 分数据中心,凭证只在账户所属数据中心的端点上有效**:

| 数据中心 | Base URL |
|---|---|
| 新加坡 | `https://email.api.engagelab.cc` |
| 土耳其 | `https://emailapi-tr.engagelab.com` |

Instance B 的账户注册在土耳其数据中心,而环境变量沿用了 A 的新加坡端点。修复只需一行:

```
ENGAGELAB_BASE_URL=https://emailapi-tr.engagelab.com
```

**判别方法(两分钟定位)**:

1. **对照实验区分"方法错"还是"凭证错"**:用一组已知可用的凭证(如 A 实例的)打同一端点——A 返回 400 参数错误(= 认证通过),问题凭证返回 401 → 排除方法/网络,锁定凭证与端点的匹配关系;
2. **跨数据中心探测**:拿同一组凭证打另一个数据中心的端点,返回非 401(哪怕是参数错误)即破案:

```bash
python -c "
import os, httpx
r = httpx.get('https://emailapi-tr.engagelab.com/v1/email_status',
    params={'date': '2026-07-03'},
    auth=(os.environ['ENGAGELAB_API_USER'], os.environ['ENGAGELAB_CREDENTIAL']), timeout=10)
print('HTTP', r.status_code, r.text[:200])
"
```

## Why This Works

EngageLab 各数据中心的账户体系相互独立:对新加坡端点而言,土耳其账户的 api_user 根本"不存在",返回的错误与"密码错误"无差别(都是 401 code 30000),因此单看错误信息永远指向凭证,形成排查死角。

## Prevention

- 新接入任何 EngageLab 账户时,**第一步确认账户所属数据中心**,`ENGAGELAB_BASE_URL` 按数据中心配置(已记入 openspec 归档 `2026-07-03-multi-instance-deployment` 的部署清单 10.9)
- 遇到"怎么换 key 都 401"时,优先做跨数据中心探测和已知好凭证对照,不要陷在 key 本身
- 400 参数错误是"认证已通过"的信号,可以当作无副作用的认证探针(`/v1/email_status` 不带正确参数即可)

## Related Issues

- openspec 归档:`openspec/changes/archive/2026-07-03-multi-instance-deployment/tasks.md`(10.9/10.14)
