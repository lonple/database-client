# DBC · Database Client

企业级 Web 数据库客户端：统一登录与组织权限，治理数据资产，在工作空间内受控执行 SQL，并留存审计。

浏览器**不直连**目标库；目标库访问只经执行面 `dbc-sqlwork`。管控面 `dbc-manage` 负责资产 / 授权 / 策略，不持目标库长连接。

[架构设计](doc/设计/架构/01-架构设计.md) · [需求设计](doc/设计/需求/01-需求设计.md) · [本地启动](doc/运维/01-本地启动说明.md) · [Docker 部署](doc/运维/02-Docker桌面部署手册.md) · [文档索引](doc/README.md)

---

## 功能概览

| 能力 | 说明 |
| --- | --- |
| 用户中心 | 登录 / JWT、用户 / 部门 / 角色、功能权限、应用 mTLS 与代签 |
| 资产管理 | 实例与连接登记、凭证加密存储、部门数据范围 |
| 权限管控 | 工作空间（公司 / 个人）、成员与连接授权、全局管控策略 |
| SQL 工作台 | 多会话编辑、按方言批执行、元数据浏览、事务会话 |
| 审计 | SQL 执行审计 + 业务操作审计（Elasticsearch） |
| 系统管理 | 应用登记等平台运维能力 |

默认账号：`admin` / `admin`（首次部署后请立即修改）。

---

## 架构一览

```text
浏览器
  → Vite / Nginx
       └─ /dbc-*  → Gateway → Nacos 负载
                      ├─ usercenter   IAM / JWT / mTLS
                      ├─ manage       资产 / 空间 / 策略
                      ├─ sqlwork      目标库执行面（唯一）
                      └─ audit        审计写入与查询（ES）
```

| 模块 | 职责 |
| --- | --- |
| `dbc-front` | Vue 3 前端（唯一 SPA） |
| `dbc-gateway` | Spring Cloud Gateway 路由 |
| `dbc-usercenter` | 身份与权限、应用证书与代签 |
| `dbc-manage` | 数据资产与工作空间管控面 |
| `dbc-sqlwork` | SQL 执行与目标库连接池 |
| `dbc-audit` | 审计 ingest / 查询 |
| `dbc-client` | 跨服务 inner 客户端（mTLS / 签名） |

服务目录名、`spring.application.name`、Gateway 路径前缀三者一致（如 `/dbc-manage/**`）。

---

## 技术栈

| 层 | 选型 |
| --- | --- |
| 后端 | Java 21 · Spring Boot 3.3 · MyBatis-Plus · Gradle |
| 网关 / 发现 | Spring Cloud Gateway · Nacos |
| 平台库 | PostgreSQL（按服务分 schema，Flyway） |
| 审计存储 | Elasticsearch（仅 `dbc-audit` 写入） |
| 缓存 | Redis（服务签名 nonce 等） |
| 前端 | Vue 3 · TypeScript · Vite · Ant Design Vue · Pinia |
| 安全 | JWT · BCrypt · AES-GCM 凭证 · 服务间 mTLS + 应用层签名 |

---

## 快速开始（Docker）

适合本机联调。**非生产部署规范**（Compose 内含明文口令、关鉴权中间件等，见运维手册「已知不足」）。

**前置**：Docker Desktop、JDK 21（构建镜像时）、仓库根可写。

```powershell
cd <repo-root>

# 日常启动
.\scripts\docker-deploy.cmd

# 改过代码后重建
.\scripts\docker-deploy.cmd -Build

# 首次或大刷新
.\scripts\docker-deploy.cmd -Full

# 停止
.\scripts\docker-stop.cmd
```

浏览器打开：<http://127.0.0.1:8080>  
账号：`admin` / `admin`

中间件与应用分两个 Compose：`deploy/middleware/`、`deploy/apps/`。详情见 [Docker 桌面部署手册](doc/运维/02-Docker桌面部署手册.md)。

---

## 本地开发启动

### 依赖

- JDK 21+
- Node.js 18+
- Nacos（发现 `8000`，控制台 `8001`）
- PostgreSQL `5432`（库 `postgres`；schema 由各服务 Flyway 创建）
- Redis `6379`
- Elasticsearch `9200`（审计必依赖）

### 发布跨服务客户端（首次必做）

```powershell
cd scripts
.\publish-dbc-client.ps1
# 或：cd dbc-client ; .\gradlew.bat publishToMavenLocal
```

### 启动顺序

```powershell
# 1. 基础设施：PostgreSQL / Redis / ES / Nacos standalone

# 2～5. 业务服务（可并行）
cd dbc-usercenter ; .\gradlew.bat bootRun   # :8004
cd dbc-manage     ; .\gradlew.bat bootRun   # :8006
cd dbc-sqlwork    ; .\gradlew.bat bootRun   # :8007
cd dbc-audit      ; .\gradlew.bat bootRun   # :8008

# 6. 网关
cd dbc-gateway    ; .\gradlew.bat bootRun   # :8003

# 7. 前端
cd dbc-front
npm.cmd install
npm.cmd run dev                             # :8005
```

开发入口：<http://127.0.0.1:8005>（Vite 将 `/dbc-*` 代理到 Gateway）。

密钥与 mTLS 材料位于仓库根 `secrets/`（已 gitignore，启动用户中心时会按需生成）。工作目录须为**仓库根**。完整说明见 [本地启动说明](doc/运维/01-本地启动说明.md)。

### 端口约定

| 服务 | 端口 |
| --- | --- |
| Nacos / 控制台 | 8000 / 8001 |
| gateway | 8003 |
| usercenter | 8004（mTLS 8044） |
| front (dev) | 8005 |
| manage | 8006 |
| sqlwork | 8007 |
| audit | 8008（mTLS ingest 8048） |

---

## 仓库结构

```text
database-client/
├── dbc-front/          # 前端
├── dbc-gateway/        # 网关
├── dbc-usercenter/     # 用户中心
├── dbc-manage/         # 资产管理 / 权限管控
├── dbc-sqlwork/        # SQL 工作台
├── dbc-audit/          # 审计
├── dbc-client/         # 跨服务客户端库
├── deploy/             # Docker Compose
├── scripts/            # 部署与发布脚本
├── drivers/            # JDBC 驱动（按需）
├── secrets/            # 本地密钥（不入库）
└── doc/                # 设计 / 规范 / 运维文档
```

各业务服务为**独立 Gradle 工程**（非单一 root 多模块）。IDEA 需分别 Link 各工程的 `build.gradle.kts`。

---

## 文档

| 文档 | 内容 |
| --- | --- |
| [doc/README.md](doc/README.md) | 文档总索引 |
| [需求设计](doc/设计/需求/01-需求设计.md) | 业务规格与功能清单 |
| [架构设计](doc/设计/架构/01-架构设计.md) | 技术架构与选型 |
| [详细设计](doc/设计/详细设计/) | 各模块与横向能力 |
| [编码规范](doc/规范/01-Java编码规范.md) | Java / 模块约定 |
| [运维](doc/运维/) | 本地启动与 Docker |

---

## 安全说明

- **勿将** `secrets/`、证书、JWT 密钥、数据库口令提交到 Git。
- 开源前请确认仓库中无真实生产凭证；示例 Compose 中的口令仅供本地联调。
- 服务间调用：用户 JWT 走公网 API；`/inner/**` 走 mTLS / 应用层签名，详见 [服务间请求签名](doc/设计/详细设计/04-服务间请求签名.md)。
- 生产环境需自行补齐：密钥托管（KMS）、中间件鉴权、多实例与备份、资源限额等（见运维手册「已知不足」）。

---

## 贡献

欢迎 Issue 与 Pull Request。较大改动建议先开 Issue 对齐设计口径（与 [doc/](doc/) 保持一致）。提交前请确保：

- 本地可编译 / 关键用例通过
- 异常日志带完整栈（见仓库规范）
- 不引入明文密钥或 demo 级捷径而不标注

---

## License

[Apache License 2.0](LICENSE)
