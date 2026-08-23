# 跨层思考指南

本仓库一条数据流：PostgreSQL → `services/*.py`（SQL + 序列化）→ `api/*`（Pydantic + 响应壳）→ `shared-types` / `shared-api`（手写）→ 页面（React Query）。**没有任何自动同步**，每一层都要人工对齐。

## 改动类型 → 必须同步的层

| 改动 | 必须一起做 |
|---|---|
| 新增 / 删除 / 改名列 | alembic revision → 重跑 `scripts/schema_snapshot.py` 并提交快照 → service SQL 与序列化 → Pydantic 响应（如有）→ `shared-types` → 页面引用 → 测试 |
| 改枚举 / 状态取值 | 数据库 CHECK → Pydantic `Literal` → `enums.ts` / 字面量联合 → Badge tone 映射 → 筛选选项 |
| 新端点 | route（静态先于动态）→ Pydantic → service → `shared-api` 函数 + 泛型 → `queryKeys` → 页面 |
| 改统计口径 | SQL FILTER → Neon 断言 → `backend/domain-rules.md` 更新 → 仪表盘文案 |
| 改发送 / 时区逻辑 | worker 与 service 两处 → `beijing_time` 工具 → mock 参数断言 + Neon 断言 → `backend/domain-rules.md` |
| 改 sanitize / 转义 | 写入点、存量面、所有出口三张清单（`backend/quality-guidelines.md`） |

## 边界问题清单（动手前自问）

1. 这个值在哪一层产生、在哪一层消费？中间有没有会改变它的层（序列化、别名、`.mappings()` 撞名）？
2. 事务边界在哪？一请求一事务；worker 自己开事务；批处理单条失败要不要回滚整轮？
3. 两实例共库：这条 SQL 会不会跨实例读写？锁是不是按实例？开关按实例？
4. 分区表：主键 / 唯一约束是否含 `created_at`？跨分区去重在应用层做了吗？
5. 多写入方：worker、webhook、对账谁会推进这个状态？幂等闸门放在哪？
6. 时间：会话 UTC、业务锚点北京；范围边界是带时区的 datetime 吗？
7. 前端缓存：key 含 tenant scope 吗？mutation 后 invalidate 了吗？SSR 预取 key 一致吗？
8. 失败路径：外部调用失败怎么分类？会不会把"没发出去"记成"失败已发"？

## 反例（都发生过）

- 改了 sanitize 只保新写入，7 个存量模板仍脏，且 `send_test_email` 不走 sanitize（PR #90 / #92）。
- 回调幂等放在 `emails.status`，被 webhook 无条件推进到 delivered 后闸门失效。
- 迁移重建表改了主键类型，worker JOIN 崩溃。
- 查询别名与另一张表同名，字段错值潜伏数月。
- 额度耗尽没有熔断，一夜把 13,950 封排队邮件打成 failed。
