## 1. 血缘模型与数据补全脚本

- [ ] 1.1 新增 wmt lineage 查询模块或脚本，按 `wc.sys_company_id -> wr.sys_company_id -> wr.source_competitor -> lx.entname_eng` 生成 wmt company 到 keyword_master 的映射
- [ ] 1.2 为 lixiaoyun clean 缺失场景增加 raw fallback：`wr.source_competitor -> lixiaoyun_api_companies.entname_eng -> keyword_master_id`
- [ ] 1.3 增加 unresolved lineage 诊断输出，至少包含 wmt id、wmt company_name、raw id、source_competitor、source_keyword、原因
- [ ] 1.4 增加一次性补全逻辑：APCB 批次从 lixiaoyun raw 补回关键词血缘；Kinwong 批次保持待确认，不自动模糊归因
- [ ] 1.5 支持 dry-run 与 write 两种模式；write 模式必须先生成受影响 `tenant_companies` 快照

## 2. tenant_companies 修复与 fan-out 改造

- [ ] 2.1 改造或停用 `backend/app/workers/fan_out.py` 旧 clean_company 写入路径，禁止继续写旧 `clean_companies.id`
- [ ] 2.2 新增 wmt lineage fan-out：按 active `tenant_keyword` 将匹配的 wmt company 写入 `tenant_companies`
- [ ] 2.3 修复悬空旧关联：对只能 JOIN 旧 `clean_companies`、不能 JOIN wmt 的 visible `tenant_companies` 做隐藏或按用户确认策略处理
- [ ] 2.4 保持 `(tenant_id, clean_company_id)` 幂等，重复 fan-out 不产生重复记录
- [ ] 2.5 为关键 JOIN 补必要索引：`waimaotong_raw_companies.sys_company_id`、`waimaotong_raw_companies.source_competitor`、`lixiaoyun_api_clean_companies.entname_eng` 如缺失则补

## 3. 测试覆盖

- [ ] 3.1 增加 clean 主路径测试：wmt raw source_competitor 匹配 lixiaoyun clean entname_eng 时写入正确 tenant_companies
- [ ] 3.2 增加 raw fallback 测试：lixiaoyun clean 缺失但 raw 存在时仍可按 keyword_master_id 写入
- [ ] 3.3 增加 unresolved 测试：无法精确匹配 clean/raw 时不写 tenant_companies，并输出诊断
- [ ] 3.4 增加旧 fan-out 防回归测试：fan-out 后 `tenant_companies.clean_company_id` 必须能 JOIN wmt 表
- [ ] 3.5 增加 tenant 列表契约测试：列表只返回当前租户 active 关键词匹配的 wmt 公司

## 4. 本地验证

- [ ] 4.1 在本地库或线上快照上运行 dry-run，核对输出包含 wmt 总数、clean 主路径数量、raw fallback 数量、unresolved 数量
- [ ] 4.2 预期当前线上快照数量：wmt clean 506，clean 主路径约 481，raw fallback 约 16，Kinwong unresolved 约 9
- [ ] 4.3 执行后端相关测试：fan-out、tenant companies API、tenant ops filters/export 相关测试
- [ ] 4.4 grep 确认 tenant 可见关系生成路径不再活跃写入旧 `clean_companies.id`

## 5. 生产执行门禁

- [ ] 5.1 生产 dry-run：只读输出每个租户预计 visible wmt 数量、新增数量、悬空旧关联数量、unresolved 清单
- [ ] 5.2 用户确认 dry-run 后，才允许执行 write 模式补全与修复
- [ ] 5.3 write 执行后验证：`tenant_companies JOIN waimaotong_clean_companies` 非 0，旧 clean-only visible 关联归零或被隐藏
- [ ] 5.4 验证 tenant 页面公司列表加载出数据，且只包含当前租户 active 关键词匹配的 wmt 公司
- [ ] 5.5 如涉及镜像发布，按仓库发布流程手动触发构建和 Sealos 更新；本任务不自动上线
