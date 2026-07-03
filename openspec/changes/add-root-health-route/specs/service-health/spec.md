# service-health

## ADDED Requirements

### Requirement: 根路径 SHALL 返回探活成功响应

后端 `GET /` SHALL 返回 HTTP 200 与 JSON `{"status": "ok"}`,供平台探活/负载均衡使用;该路由 MUST NOT 要求认证,MUST NOT 访问数据库。

#### Scenario: 探活请求根路径

- **GIVEN** 服务正常运行
- **WHEN** 任意来源 GET `/`
- **THEN** 返回 200 与 `{"status": "ok"}`,访问日志不再出现根路径 404
