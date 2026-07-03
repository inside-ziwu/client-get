## 1. 实施

- [x] 1.1 main.py 新增 `GET /` 路由返回 `{"status": "ok"}`
- [x] 1.2 新增测试 `test_root_health.py` 覆盖 200 与响应体

## 2. 发布

- [x] 2.1 r6 起包含,A/B 已升级(现 r7);2026-07-03 实测 A/B 生产 `GET /` 均返回 `{"status":"ok"}`
