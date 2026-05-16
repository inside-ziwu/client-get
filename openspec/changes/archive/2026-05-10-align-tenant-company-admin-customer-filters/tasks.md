## 1. 现状确认

- [x] 1.1 对照 admin 客户数据页、tenant 公司列表、tenant 优选客户现有筛选项，列出共同基础筛选、tenant-only 筛选和 admin-only 筛选
- [x] 1.2 确认 `v3-tenant-companies` 中 C5 筛选未完成任务与本 change 的重叠范围，避免重复实现同一行为
- [x] 1.3 确认当前后端字段来源：`clean_companies`、`clean_company_sources`、`tenant_companies` 中各筛选字段的真实列名和空值表现
- [x] 1.4 按 `design.md` 的最终筛选契约表复核字段名、UI 控件、外部参数和后端列；如发现不一致，先更新契约表再实施

## 2. 共享筛选契约

- [x] 2.1 在前端 shared API 或相邻 shared 模块中定义 base company filter 类型、选项和档位常量，外部参数以 `design.md` 最终筛选契约表为准
- [x] 2.2 实现 tenant 与 admin 共用的筛选参数 mapper，覆盖关键词、国家、行业、产品标签、来源、员工人数范围、成立日期年份范围、进口额、进口次数、联系人、PCB 供应商；员工规模输出 `employee_count_min` / `employee_count_max`，成立日期输出 `founded_year_from` / `founded_year_to`，PCB 供应商输出 `pcb_supplier_presence=has|none`
- [x] 2.3 明确 tenant-only advanced filters 的类型与 mapper，使其与共享基础筛选分离
- [x] 2.4 为 shared mapper 增加单元测试，覆盖多选 OR、范围、联系人档位和空值清理

## 3. 后端筛选语义对齐

- [x] 3.1 调整 admin clean companies API 入参，使其支持共享基础筛选契约的多选、范围和档位语义
- [x] 3.2 调整 admin clean companies 查询条件，使其与 tenant 基础筛选使用等价的 `clean_companies` / `clean_company_sources` 谓词
- [x] 3.3 调整 tenant companies API 入参或兼容层，使其接受共享基础筛选契约，同时保留租户可见性约束
- [x] 3.4 调整 tenant companies 查询条件，使共享基础筛选与 admin 等价，tenant-only 筛选额外叠加
- [x] 3.5 后端员工规模筛选必须把 `employee_num` 解析为人数或人数区间后匹配 `employee_count_min` / `employee_count_max`，不能使用 `employee_num IN (...)` 精确匹配
- [x] 3.6 admin 后端直接迁移到 `pcb_supplier_presence=has/none`，不保留旧 `pcb=yes/no` 共享契约；实施前用代码搜索确认没有外部或同仓调用方仍依赖旧参数
- [x] 3.7 增加后端测试，验证同一基础筛选在 admin 与 tenant 服务层使用一致语义，tenant 结果只因可见性被裁剪

## 4. 前端页面对齐

- [x] 4.1 更新 tenant 公司列表筛选 UI，使基础筛选项、标签、档位和参数 mapper 与共享契约一致
- [x] 4.2 更新 tenant 优选客户筛选 UI，使基础筛选项、标签、档位和参数 mapper 与共享契约一致
- [x] 4.3 更新 admin 客户数据页筛选 UI，使基础筛选项、标签、档位和参数 mapper 与共享契约一致
- [x] 4.4 三处页面均将成立日期筛选文案显示为“成立日期”，控件选择年份并提交 `founded_year_from` / `founded_year_to`
- [x] 4.5 将 tenant-only 筛选在 UI 上与共享基础筛选分组区分，避免被误认为 admin 必须存在的基础筛选
- [x] 4.6 确认查询、重置、分页切换和已选筛选展示不会使用旧字段名或旧档位
- [x] 4.7 将联系人数从固定档位改为 `contact_count_min` / `contact_count_max` 数值区间，并让三处页面区间控件统一使用 `～` 连接
- [x] 4.8 优化三处筛选区交互布局，将基础条件、区间条件、租户专属条件分组排布，避免所有控件堆叠在同一行
- [x] 4.9 优化筛选控件暗文案，并显式拉开筛选条件上下行距，避免换行后贴在一起
- [x] 4.10 按最新裁决将三处筛选条件改为平铺展示，移除“基础条件 / 区间条件 / 租户专属”等分类 key 或标题，只保留实际筛选和操作项

## 5. 验证与收尾

- [x] 5.1 运行后端相关测试，至少覆盖 admin collection clean companies 与 tenant company query
- [x] 5.2 运行前端相关测试或类型检查，至少覆盖 shared mapper 与受影响页面
- [x] 5.3 手工验收 admin 客户数据页、tenant 公司列表、tenant 优选客户的同一基础筛选组合，记录差异只来自 tenant 可见性或优选客户自身范围（用户已在线上验证）
- [x] 5.4 更新本 change 的任务勾选状态，并在完成汇报前调用 `verification-before-completion` skill
