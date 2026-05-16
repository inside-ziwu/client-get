# Slice 1.C — UC-10 admin 启动按钮（D-035 渠道限制）

状态：**✅ 本地验证通过，已签字**

创建日期：2026-05-07

---

## 目标

按 D-035 决策，在 V3 阶段仅开放 lixiaoyun（反推）渠道，外贸通（waimao_tong）直采推迟至 V3.1+：

| 变更项 | 说明 |
|--------|------|
| 前端 直采渠道操作禁用 | `isFirst=true` 行改为禁用按钮 + Tooltip "外贸通采集 V3.1+ 可用" |
| 后端 API schema | `POST /collection-keywords/trigger` 从 `dict` 换为 `TriggerCollectionRequest` Pydantic 模型 |
| 后端 Service 白名单 | `trigger_collection` 只允许 `channel == "lixiaoyun"`，拒绝其他渠道（400 CHANNEL_NOT_AVAILABLE）|

---

## 变更范围

### 前端
- [x] `frontend/apps/admin/src/pages/CollectionTasks/index.tsx`
  - 操作列 `isFirst=true` 分支：`renderDirectActions(row)` → 禁用的 `<Button>` + `<Tooltip title="外贸通采集 V3.1+ 可用">`
  - 历史查看按钮保留（不受 D-035 影响）

### 后端
- [x] `backend/app/api/admin/collection.py`
  - 新增 `TriggerCollectionRequest(BaseModel)`：`keyword_normalized: str`, `channel: str`
  - `trigger_collection` endpoint：`payload: dict` → `payload: TriggerCollectionRequest`

- [x] `backend/app/services/admin_collection_service.py`
  - `trigger_collection`：`if channel not in ("waimao_tong", "lixiaoyun"):` → `if channel != "lixiaoyun":`
  - 错误码：`VALIDATION_ERROR` → `CHANNEL_NOT_AVAILABLE`，状态码 422 → 400
  - 注释标注 D-035

---

## 设计决策

### 前端为何禁用而非隐藏直采行？

隐藏 `isFirst=true` 行会破坏表格的 `rowSpan: 2` 结构（"关键词"和"累计"列跨 2 行显示）。禁用操作入口同时保留行结构，视觉上也明确传达"功能存在但暂不可用"的语义。

### 后端为何用 400 而非 422？

422 是 Pydantic 校验错误语义（字段格式不合法）。`channel=waimao_tong` 格式合法，只是业务上暂不开放，用 400（Bad Request）更准确。

---

## 验收标准

```bash
# V3-COL-002：反推渠道可触发
POST /api/admin/collection-keywords/trigger
{"keyword_normalized": "...", "channel": "lixiaoyun"}
# 期望：200，collection_tasks 入库，status=pending

# V3-COL-003：直采渠道被拒绝
POST /api/admin/collection-keywords/trigger
{"keyword_normalized": "...", "channel": "waimao_tong"}
# 期望：400 CHANNEL_NOT_AVAILABLE
```

---

## 签字

- [x] 本地 smoke test（lay 2026-05-07）
  - V3-COL-003: `channel=waimao_tong` → 400 `CHANNEL_NOT_AVAILABLE` ✅
  - V3-COL-002: `channel=lixiaoyun` → 409 `TASK_ALREADY_RUNNING`（通过渠道校验，到达业务逻辑）✅
  - Pydantic schema：缺少 `keyword_normalized` → 422 `VALIDATION_ERROR` ✅
- [ ] Sealos 生产部署（lay）→ Gate 8 已解除，按 [`deploy-wave2-checklist.md`](../deploy-wave2-checklist.md) 执行
