# ClientGet Web

ClientGet 前端包含两个 Vite 应用：

- `apps/admin`：平台管理端
- `apps/tenant`：租户端

两个应用都通过 `@shared/api` 访问后端真实接口，不再依赖页面内 mock 数据。

## 安装与本地运行

```bash
pnpm install
pnpm dev:admin
pnpm dev:tenant
```

默认端口：

- Admin: `http://localhost:3000`
- Tenant: `http://localhost:3001`

## 环境变量

两个应用都需要：

- `VITE_API_BASE_URL`

开发环境示例已经放在：

- [apps/admin/.env.example](apps/admin/.env.example)
- [apps/tenant/.env.example](apps/tenant/.env.example)

开发时默认值：

```bash
VITE_API_BASE_URL=http://localhost:8000
```

生产时填写后端 API 根域名，例如：

```bash
VITE_API_BASE_URL=https://api.example.com
```

前端会在运行时自动拼接：

- Admin: `${VITE_API_BASE_URL}/admin/api/v1/*`
- Tenant: `${VITE_API_BASE_URL}/t/{slug}/api/v1/*`

Tenant 前端路由本身不带 slug；slug 只来自登录输入和 JWT payload。

## 构建校验

```bash
pnpm type-check
pnpm build
```

## 联调账号

后端执行 `backend/scripts/seed_demo_data.py` 后可使用：

- `globex-pcb` / `owner@globex.example.com` / `ChangeMe123!`
- `acme-pcb` / `owner@acme.example.com` / `ChangeMe123!`

其中：

- `globex-pcb` 用于主路径联调
- `acme-pcb` 用于 onboarding 联调

## 发布前核对

- `VITE_API_BASE_URL` 指向正确的后端域名
- Admin/Tenant 域名已加入后端 `ALLOWED_ORIGINS`
- 浏览器可完成 Admin 登录与 Tenant 登录
- Tenant 页面无 mock 列表残留
