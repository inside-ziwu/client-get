## 1. 后端筛选与分页

- [ ] 1.1 列表接口增加查询参数：status、keyword（模糊搜索）、date_from、date_to、page、page_size
- [ ] 1.2 service 层 list_sending_plans 增加 WHERE 条件（status 精确匹配、name ILIKE 模糊搜索、created_at 范围）和 LIMIT/OFFSET 分页；date_to 包含当天（加一天处理）
- [ ] 1.3 单独 COUNT(*) 查询返回 total 总数，前端据此计算总页数

## 2. 后端状态检查与 complete-update

- [ ] 2.1 update_sending_plan 方法开头检查 status，非 draft 则 403；加 FOR UPDATE 锁
- [ ] 2.2 delete_sending_plan 方法开头检查 status，不在 (draft, completed, cancelled) 则 403；加 FOR UPDATE 锁
- [ ] 2.3 新增 POST /sending-plans/{plan_id}/complete-update 端点，原子替换 plan 基本信息 + 删除旧 steps 并插入新 steps + 处理 recipients 变更（recipient_config）
- [ ] 2.4 complete-update 方法开头检查 status，非 draft 则 403；加 FOR UPDATE 锁

## 3. 前端类型扩展

- [ ] 3.1 PlanFilters 增加 date_from、date_to、page、page_size 字段

## 4. 前端列表筛选与分页

- [ ] 4.1 列表顶部增加状态筛选下拉（全部/草稿/已排期/执行中/已暂停/已完成/已取消）
- [ ] 4.2 列表顶部增加名称搜索框（防抖处理）
- [ ] 4.3 列表顶部增加日期范围筛选
- [ ] 4.4 列表底部增加分页组件（参考 companies 页面：上一页/下一页/页码输入/每页条数选择/共X条）

## 5. 前端行操作菜单与显示优化

- [ ] 5.1 每行末尾增加「...」操作菜单按钮（DropdownMenu 组件）
- [ ] 5.2 根据计划状态动态展示菜单项（草稿：详情/编辑/删除；已完成/已取消：详情/删除；已排期/执行中/已暂停：仅详情）
- [ ] 5.3 点击行（非操作菜单区域）进入详情页
- [ ] 5.4 删除操作增加二次确认弹窗（AlertDialog），确认后调用 DELETE 接口
- [ ] 5.5 创建时间列改为日期+时间格式（YYYY-MM-DD HH:mm）
- [ ] 5.6 移除进度条列

## 6. 编辑模式

- [ ] 6.1 新增路由 /send-plans/[id]/edit/page.tsx，加载 plan 详情 + steps + recipient_config 数据
- [ ] 6.2 向导组件抽取为可复用部分，支持初始数据传入（新建传 defaultFormData，编辑传加载数据）
- [ ] 6.3 编辑模式提交调用 complete-update 端点而非 complete-create
- [ ] 6.4 编辑模式页面标题改为「编辑发送计划」，提交按钮改为「保存修改」

## 7. 前端 API 客户端与缓存键

- [ ] 7.1 sending-plans.ts 新增 completeUpdate 方法
- [ ] 7.2 统一缓存键为 ['tenant', 'sendingPlans']，修复列表页与向导 invalidation 不一致

## 8. 验证

- [ ] 8.1 筛选：按状态（含已排期）、名称、日期范围筛选，确认结果正确；多条件组合筛选
- [ ] 8.2 分页：翻页后数据正确，筛选条件保持；页码输入跳转正常；总数与 COUNT(*) 一致
- [ ] 8.3 编辑草稿：点击编辑进入向导，数据已预填（基本信息+步骤+收件人来源配置），修改后保存成功
- [ ] 8.4 删除：确认弹窗出现，确认后计划消失；执行中/已排期计划无法通过 API 删除
- [ ] 8.5 状态约束：已排期/执行中/已暂停计划的操作菜单无编辑/删除选项
- [ ] 8.6 行点击进入详情页正常
- [ ] 8.7 时间格式显示为日期+时间；进度条列已移除
- [ ] 8.8 创建/编辑后列表自动刷新（缓存键一致性验证）
