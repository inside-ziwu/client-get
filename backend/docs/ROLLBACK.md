# Rollback

## 适用范围

- 代码发布失败
- worker 新逻辑导致持续报错
- 前端已发布但后端接口契约回退

## 代码回滚

1. 切回上一版镜像或上一版代码
2. 重新启动：

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build backend collection-scheduler collection-worker scoring-worker sending-worker
```

## 数据边界

- 本项目不提供自动数据库降级迁移
- 如果某次发布已经执行 `alembic upgrade`，默认回滚边界是“保留新 schema，回退应用代码”
- 需要真正回退数据库时，必须先确认：
  - 新迁移是否只新增字段/表
  - 回滚后旧代码是否还能读取新 schema

## 建议流程

1. 先回退应用与全部 worker
2. 保持数据库不降级
3. 验证 Admin/Tenant 登录、关键列表页、collection/scoring/sending worker 健康
4. 只有在 schema 明确兼容失败时，才讨论人工数据库回退
