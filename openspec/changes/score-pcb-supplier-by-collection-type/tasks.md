## 1. 实施

- [x] 1.1 `has_china_pcb_supplier` 条件按 `compute_collection_type == "reverse"` 判定,复用单一真源,兼容 jsonb 字符串形态
- [x] 1.2 移除恒告警;新增单元测试覆盖 精准反推 20 分 / 关键词采集 10 分 / NULL 口径 / 字符串形态

## 2. 发布与存量

- [ ] 2.1 随 backend 镜像发布,A/B 后端与 Worker 更新 tag(新评分与补评即时生效)
- [x] 2.2 决策存量重算:用户选定 a) 全量重算。新增 `backend/scripts/rescore_system_scores.py`(默认 dry-run,`RESCORE_CONFIRM=yes --execute` 二重确认,分批事务,幂等可重跑,模板选择与 score_clean_company/补评完全一致)
- [x] 2.3 生产执行全量重算(2026-07-03):34,473 家公司,4,306 家分数变化;等级迁移 C→B 295、B→A 15、B→C 101(旧模板版本存量统一到 v6 的回归),其余等级不变;重算后分布 A 36 / B 8,522 / C 25,915,与迁移分布对账一致;抽查精准反推 A 级 76 分(阈值 70)正确
