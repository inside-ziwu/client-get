## 1. 实施

- [x] 1.1 main.py 新增 `GET /` 路由返回 `{"status": "ok"}`
- [x] 1.2 新增测试 `test_root_health.py` 覆盖 200 与响应体

## 2. 发布

- [ ] 2.1 随下一次 backend 镜像发布,更新 A/B 后端与 Worker 的 tag 后确认日志根路径 404 消失
