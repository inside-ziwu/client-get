## 1. 实施

- [x] 1.1 `has_china_pcb_supplier` 条件按 `compute_collection_type == "reverse"` 判定,复用单一真源,兼容 jsonb 字符串形态
- [x] 1.2 移除恒告警;新增单元测试覆盖 精准反推 20 分 / 关键词采集 10 分 / NULL 口径 / 字符串形态

## 2. 发布与存量

- [ ] 2.1 随 backend 镜像发布,A/B 后端与 Worker 更新 tag(新评分与补评即时生效)
- [ ] 2.2 决策存量重算:精准反推公司 system_score 普遍 +10(等级阈值 S90/A70/B40/C10),可选 a) 全量重算脚本 b) 将精准反推公司 system_grade 置 NULL 由补评循环渐进重算 c) 不动存量只对新公司生效
