# 外贸自动化营销系统 - 系统总览

> 文档版本：v1.0 | 基于仓库 aoqi-ai/sysdev-ft-marketing | 2026-04-16
> 用途：供 AI Agent 上下文注入 + 人类开发者参考

---

## 1. 系统定位

**一句话描述**：基于 AI + 自动化的外贸 B2B 冷邮件获客系统，从关键词搜索到邮件发送全链路自动执行。

**业务场景**：PCB 制造商（鑫安线路板）通过自动化系统，批量发现海外潜在客户、AI 评级筛选、生成个性化开发信并自动发送，实现从 0 到 1 的外贸主动获客。

**核心价值**：
- 每日可处理 1000+ 封邮件，成本约 $137/月
- 仅需两次人工介入（审批计划、审批草稿）
- AI 驱动的多维度客户评级（相关性/市场匹配/意向度）
- 多轮跟进邮件自动调度

**当前状态**：已上线运行，效果良好，计划产品化。

---

## 2. 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **后端框架** | FastAPI | 0.135.1 | REST API 服务 |
| **工作流引擎** | Prefect | 3.6.21 | 4 个自动化 Flow |
| **数据库** | PostgreSQL | - | 核心数据存储 |
| **前端框架** | React | 19 | SPA 管理后台 |
| **UI 库** | Ant Design | 6 | 组件库 |
| **构建工具** | Vite | 7 | 前端构建 |
| **AI/LLM** | OpenRouter | - | 公司评级 + 邮件生成（DeepSeek等模型） |
| **邮件服务** | EngageLab | - | 邮件发送 + 追踪（打开/点击） |
| **数据采集** | 网易外贸通 API | - | 海外公司搜索 + 联系人获取 |
| **认证** | JWT (PyJWT) | 2.12.1 | Bearer Token 认证 |
| **监控** | Prometheus | 0.24.1 | 请求指标采集 |
| **运行时** | Python | 3.11+ | 后端语言 |
| **运行时** | Node.js | 18+ | 前端开发 |

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户浏览器                              │
│                 React 19 + Ant Design 6                      │
│              http://localhost:5173                            │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API (JWT Bearer)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 后端                               │
│                 http://localhost:8000                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Auth     │ │ Plans    │ │ Keywords │ │ Dashboard│       │
│  │ Router   │ │ Router   │ │ Router   │ │ Router   │  ...  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────────┐
│  PostgreSQL  │ │ Scheduler│ │  Prefect Flows   │
│  (ft_data)   │ │ 每30秒   │ │  4个自动化工作流  │
│              │ │ 扫描计划  │ │                  │
│ 12张核心表   │ │ 分配配额  │ │ Flow01: 采集     │
│              │ │ 派发Flow  │ │ Flow02: 清洗评级 │
│              │ │          │ │ Flow03: 生成邮件 │
│              │ │          │ │ Flow04: 发送邮件 │
└──────────────┘ └──────────┘ └────────┬─────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
             ┌──────────┐      ┌──────────┐       ┌──────────┐
             │ 网易外贸通│      │ OpenRouter│       │EngageLab │
             │ 公司搜索  │      │ LLM API  │       │ 邮件发送  │
             │ 联系人获取│      │ 公司评级  │       │ 送达追踪  │
             │ 贸易数据  │      │ 邮件生成  │       │          │
             └──────────┘      └──────────┘       └──────────┘
```

---

## 4. 核心业务流程

### 4.1 计划生命周期（9 状态）

```
draft ──人工审批──▶ approved ──自动──▶ keyword_gen ──自动──▶ collecting
                                                              │
                                                              ▼ (所有关键词完成)
done ◀──自动── sending ◀──人工审批── pending_approval ◀──自动── generating ◀──自动── cleaning
```

| 状态 | 含义 | 触发方式 | 下一步 |
|------|------|----------|--------|
| `draft` | 草稿 | 创建计划 | 人工审批 → approved |
| `approved` | 已审批 | 人工操作 | 自动生成关键词 → keyword_gen |
| `keyword_gen` | 生成关键词中 | 系统自动 | 开始采集 → collecting |
| `collecting` | 采集公司中 | Flow01 运行 | 全部关键词完成 → cleaning |
| `cleaning` | 清洗评级中 | Flow02 运行 | 全部公司分析完 → generating |
| `generating` | 生成开发信 | Flow03 运行 | 草稿生成完 → pending_approval |
| `pending_approval` | 等待审批草稿 | 系统自动 | 人工审批 → sending |
| `sending` | 发送中 | Flow04 运行 | 全部发完 → done |
| `done` | 完成 | 系统自动 | - |

### 4.2 四个 Prefect Flow

| Flow | 文件 | 输入 | 输出 | 外部依赖 |
|------|------|------|------|----------|
| **01 关键词采集** | `flow_01_keyword_collect.py` | 关键词 + 国家 | 公司原始数据 | 网易外贸通 Search API |
| **02 公司清洗评级** | `flow_02_company_analysis.py` | 未分析的公司 | 评级结果(A/B/X) + 联系人 | OpenRouter LLM + 网易外贸通 Detail/Contact/BaseInfo API |
| **03 邮件生成** | `flow_03_email_draft.py` | 已筛选联系人 | 个性化开发信草稿 | OpenRouter LLM |
| **04 邮件发送** | `flow_04_email_send.py` | 已审批草稿 | 已发送邮件 | EngageLab API |

### 4.3 数据漏斗

```
关键词 → 公司(company_data) → 清洗评级(company_analysis)
                                    ├── A级: 精准匹配 (score 80-100)
                                    ├── B级: 相关行业 (score 40-60)
                                    └── X级: 不相关 (score 0, 跳过)
                                         │
                              A/B级公司 + 联系人(contact_data)
                                         │
                              联系人分级: A(采购/高管) > B(技术/生产) > X(其他)
                                         │
                              邮件草稿(email_drafts) → 审批 → 发送
```

---

## 5. 调度器（Scheduler）

`scripts/scheduler.py` - 系统的"大脑"，每 30 秒循环一次：

1. **扫描活跃计划**：按优先级排序（`priority DESC, id ASC`）
2. **检测可执行阶段**：根据数据条件判断每个计划需要运行哪个 Flow
3. **配额管理**：每日 API 配额 100,000 次，按优先级分配
4. **派发执行**：以 daemon 线程启动 Flow，含超时看门狗（60分钟）
5. **去重保护**：内存 + 数据库双重检查，防止重复派发
6. **并行管道**：同一计划可同时运行多个阶段

---

## 6. 认证与安全

- **认证方式**：JWT Bearer Token，24小时有效期
- **默认账号**：admin / admin123（生产环境需更改）
- **密码存储**：bcrypt 哈希存储在 `system_config` 表
- **敏感信息**：API Key、Cookie 等存储在 `system_config` 表或环境变量
- **CORS**：当前 `allow_origins=["*"]`（产品化需收紧）

---

## 7. 关键限制与约束

| 约束 | 当前值 | 说明 |
|------|--------|------|
| 每日邮件配额 | 2,500 封/天 | EngageLab 限制 |
| 每日 API 配额 | 100,000 次/天 | 网易外贸通限制 |
| 关键词每日页数 | 10 页/关键词/天 | 防封限制 |
| 每页公司数 | 100 条 | API 单次返回 |
| LLM 并发 | 5 workers (清洗) / 12 workers (邮件) | Prefect ConcurrentTaskRunner |
| 发送时间窗口 | 收件人当地工作日 9:00-17:00 | 时区感知 |
| 多轮邮件 | 最多 7 轮 | 通过 linked_plan_id 关联 |
| Flow 超时 | 60 分钟 | 调度器看门狗 |

---

## 8. 目录结构

```
sysdev-ft-marketing/
├── main_api.py              # FastAPI 入口
├── api/                     # API 路由层（11 个路由模块）
│   ├── deps.py              # 数据库连接池
│   ├── auth_middleware.py   # JWT 中间件
│   ├── routes_auth.py       # 认证
│   ├── routes_plans.py      # 计划管理（核心，最复杂）
│   ├── routes_dashboard.py  # 仪表盘统计
│   ├── routes_companies.py  # 公司列表
│   ├── routes_contacts.py   # 联系人
│   ├── routes_drafts.py     # 草稿管理
│   ├── routes_keywords.py   # 关键词 CRUD
│   ├── routes_templates.py  # 邮件模板
│   ├── routes_product_config.py  # 清洗规则配置
│   ├── routes_tasks.py      # 任务运行管理
│   └── routes_company_assets.py  # 原始公司数据
├── flows/                   # Prefect 工作流
│   ├── flow_01_keyword_collect.py
│   ├── flow_02_company_analysis.py
│   ├── flow_03_email_draft.py
│   ├── flow_04_email_send.py
│   ├── config.py            # 全局配置常量
│   └── utils/               # 工具模块
│       ├── db.py            # 数据库操作
│       ├── netease_api.py   # 网易外贸通 API 客户端
│       ├── llm.py           # OpenRouter LLM 客户端
│       ├── engagelab.py     # EngageLab 邮件 API
│       ├── email_validator.py  # 邮箱验证（语法+MX）
│       ├── warmup.py        # 域名预热 & 配额管理
│       └── browser_cookie.py   # 网易外贸通登录态管理
├── scripts/
│   ├── scheduler.py         # 计划驱动调度器
│   └── migrate_*.py         # 数据库迁移脚本
├── web/                     # React 前端
│   └── src/
│       ├── pages/           # 12 个页面组件
│       ├── api/             # Axios API 封装
│       ├── router/          # 路由定义
│       ├── layouts/         # AdminLayout 布局
│       └── components/      # 共享组件
├── tests/                   # 测试套件
└── docs/                    # 文档
```

---

## 9. 产品化背景（升级方向）

当前系统是**单用户内部工具**，升级目标是**多租户 SaaS 产品**，面向外贸业务人员（非技术背景）。

已确认的升级诉求：
- 多租户架构
- 计费与订阅系统
- 权限与团队管理
- 用户体验升级（面向非技术用户）
- 数据源扩展（不仅限于网易外贸通）

详见 `06_PRODUCTIZATION_GAP.md`。
