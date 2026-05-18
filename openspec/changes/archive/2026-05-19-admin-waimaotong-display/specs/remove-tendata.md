## RM-TENDATA-01: Admin 端 SHALL 移除腾道数据页面

**Given** 用户访问 Admin 端
**When** 查看侧边栏导航
**Then** 不存在"腾道"入口，存在"外贸通"入口

## RM-TENDATA-02: `/collection/tendata` 路由 SHALL 不可访问

**Given** 用户直接访问 `/collection/tendata`
**When** 页面加载
**Then** 返回 404 或重定向

## RM-TENDATA-03: 后端 tendata 共享筛选分支 SHALL 不影响 waimaotong

**Given** 后端 `list_v3_raw_companies()` 中 tendata 和 waimaotong 原本共享 WHERE 分支
**When** 重构后
**Then** waimaotong 拥有独立筛选分支，不引用任何 tendata 专有列（country_iso3, trade_amount_3y_usd, trade_count, raw_payload 等）
