# _control

`_control/` 只保存 OpenSpec 之外仍有长期价值的输入、证据和历史归档。

## 权威顺序

实施、修复、重构、部署变更时，权威顺序固定为：

1. `openspec/changes/<change-id>/proposal.md`
2. `openspec/changes/<change-id>/design.md`（如存在）
3. `openspec/changes/<change-id>/tasks.md`
4. `openspec/changes/<change-id>/specs/*`（如存在）
5. `_control/` 中被当前 change 明确引用的输入或证据

`_control/` 不能覆盖 active OpenSpec change。若发现 `_control/` 与当前 change 冲突，必须先更新 change，再继续实施。

## 目录

| 目录 | 用途 | 读写规则 |
| --- | --- | --- |
| `inputs/` | 业务目标、参考实现、数据库访问协议、schema 等输入材料 | 默认只读；只有对应 change 要求时才更新 |
| `mockups/` | UI 原型输入 | 默认只读；实现时按当前 change 引用 |
| `evidence/` | 已完成 slice 记录、部署清单、数据库 dump / snapshot 等证据 | 可追加新证据；不要改写历史事实 |
| `archive/` | 旧计划、旧问题清单、review 轮次、占位文档 | 仅追溯历史时读取，不作为当前实施依据 |

## 约定

- 新问题不要写进 `_control/04-open-questions.md` 这类全局清单；应写入当前 OpenSpec change 的 `proposal.md` / `design.md` / `tasks.md` / `specs/*`。
- 项目现状调研不要长期维护在 `_control/` 根目录；每个 change 自己调研并沉淀到该 change。
- Review 结论如果会影响实施，必须进入对应 change；原 review 文件只作为归档证据。
