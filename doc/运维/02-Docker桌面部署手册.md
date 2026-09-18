# 02 Docker Desktop 安装部署手册

> **定位**：Windows + Docker Desktop，中间件与前后端 **分两个 Compose** 部署。  
> **环境级别**：本地学习 / 联调。**不是生产规范。**  
> **宿主机数据根目录**：由用户指定，写入 `deploy/dbc-docker.env` 的 `DBC_DOCKER_WORKSPACE`（勿提交 Git）。

---

## 0. 结论

| Compose | 路径 | 内容 |
| --- | --- | --- |
| 中间件 | `deploy/middleware/docker-compose.yml` | PostgreSQL / Redis / Nacos / Elasticsearch |
| 前后端 | `deploy/apps/docker-compose.yml` | gateway / usercenter / manage / sqlwork / audit / front |

共用外部网络：`dbc-net`（由中间件 Compose 创建）。

**推荐用法（同一脚本：首次部署 + 以后每天启动）：**

在仓库根目录打开终端（PowerShell 或 CMD 均可），复制整行执行：

```powershell
cd <repo-root>

# 首次：指定数据目录（任选本机路径，例如 D:\data\dbc）
.\scripts\docker-deploy.cmd -WorkspaceRoot D:\data\dbc

# 日常启动（复用 deploy\dbc-docker.env）
.\scripts\docker-deploy.cmd

# 改过代码
.\scripts\docker-deploy.cmd -Build

# 首次或大刷新
.\scripts\docker-deploy.cmd -Full

# 停止
.\scripts\docker-stop.cmd
```

> 不要只写 `docker-deploy.ps1`：Windows 默认禁止直接跑 `.ps1`。请用上面的 **`.cmd`**（已内置 Bypass），或：
> `powershell -ExecutionPolicy Bypass -File .\scripts\docker-deploy.ps1`

浏览器：`http://127.0.0.1:8080`（`admin` / `admin`）。细则见 **§10**。

**已知不足 / 非生产**（上线前必须改）：Compose 内明文口令、Nacos/ES 关鉴权、密钥目录明文挂载、单实例、无资源限额与备份策略。

---

## 0.1 数据目录怎么指定

优先级（高 → 低）：

1. 参数 `-WorkspaceRoot <路径>`
2. 环境变量 `DBC_DOCKER_WORKSPACE`
3. 已存在的 `deploy/dbc-docker.env`
4. 交互提示（仅 `docker-deploy` / `init-docker-workspace` / `build-docker-apps`；回车默认 `%USERPROFILE%\dbc-docker-data`）

手工编辑示例：复制 `deploy/dbc-docker.env.example` → `deploy/dbc-docker.env`：

```env
DBC_DOCKER_WORKSPACE=D:/data/dbc
```

手跑 Compose 时务必带上 env 文件：

```powershell
docker compose --env-file deploy/dbc-docker.env -f deploy/middleware/docker-compose.yml up -d
docker compose --env-file deploy/dbc-docker.env -f deploy/apps/docker-compose.yml up -d --build
```

更换数据目录后，旧目录数据不会自动迁移；需自行拷贝或重新初始化。

---

## 1. 镜像

### 1.1 需提前 pull 的基础/中间件镜像（断网环境）

```powershell
docker pull postgres:18
docker pull redis:8.8.2
docker pull nacos/nacos-server:v3.2.4-slim
docker pull elasticsearch:9.2.3
docker pull eclipse-temurin:21.0.12_8-jre
docker pull node:26.8.2-slim
docker pull nginx:stable-alpine
```

### 1.2 用途对照

| 镜像 | 用途 |
| --- | --- |
| `postgres:18` | 平台库 |
| `redis:8.8.2` | nonce |
| `nacos/nacos-server:v3.2.4-slim` | 服务发现 |
| `elasticsearch:9.2.3` | 审计 |
| `eclipse-temurin:21.0.12_8-jre` | 五个 Java 服务运行时基础镜像 |
| `node:26.8.2-slim` | 前端 Dockerfile 构建阶段 |
| `nginx:stable-alpine` | 前端最终镜像基础（亦被 `dbc-front` 使用） |
| `dbc-*:0.1.0`（本地 build） | 业务镜像，由 Compose/`Dockerfile` 生成，无需 pull |

架构基线曾写 PostgreSQL 16；你当前使用 18。若遇兼容问题改回 `postgres:16`。

---

## 2. 宿主机目录（全部在 `E:\app\docker\workspace\dbc`）

```text
E:\app\docker\workspace\dbc\
  postgres\data            # 挂载到容器 /var/lib/postgresql（PG18+ 要求，勿再挂 .../data）
  redis\data
  nacos\logs
  elasticsearch\data
  secrets\                 # 全业务共用（jwt / mTLS / kek）
  secrets\manage\drivers
  manage\drivers           # 驱动 JAR（挂到容器 drivers 目录）
  manage\logs
  usercenter\logs
  sqlwork\logs
  audit\logs
  gateway\logs
  front\html               # npm run build 产物
  front\conf\default.conf  # Nginx 配置
```

初始化：

```powershell
cd e:\workspace\database-client
powershell -ExecutionPolicy Bypass -File .\scripts\init-docker-workspace.ps1
```

会创建目录、复制 Nginx 配置，并把仓库 `secrets\` 增量同步到工作区（若存在）。

---

## 3. 端口

| 用途 | 宿主机 |
| --- | --- |
| 前端 Nginx | **8080** |
| Gateway | 8003 |
| usercenter HTTP / mTLS | 8004 / 8044 |
| manage / sqlwork / audit | 8006 / 8007 / 8008 |
| audit mTLS | 8048 |
| Nacos 发现 / 控制台 / gRPC | 8000 / 8001 / 9000 |
| PostgreSQL / Redis / ES | 5432 / 6379 / 9200 |

容器互联：Nacos 用 `nacos:8848`；库用服务名 `postgres` / `redis` / `elasticsearch`。

---

## 4. 打包 → 镜像 → 运行（代码落点）

```text
scripts/build-docker-apps.ps1          ← 打包（PowerShell）
  ├─ init-docker-workspace.ps1         ← 建 E:\app\docker\workspace\dbc\...
  ├─ publish-dbc-client.ps1            ← client → mavenLocal
  ├─ dbc-*/gradlew bootJar             ← 后端制品：build/libs/app.jar
  └─ dbc-front npm run build（可选）   ← 同步 dist 到工作区 front/html 便于查看

docker compose -f deploy/apps/... up -d --build   ← 制作镜像并运行
  ├─ dbc-*/Dockerfile                  ← COPY app.jar → eclipse-temurin:21.0.12_8-jre → 容器
  └─ dbc-front/Dockerfile              ← 镜像内 npm build → nginx 镜像 → 容器

docker compose -f deploy/middleware/... up -d     ← 官方镜像，无业务打包
```

| 步骤 | 做什么 | 代码/文件在哪 |
| --- | --- | --- |
| 1 打包后端 | `bootJar` → `app.jar` | `scripts/build-docker-apps.ps1`；各 `dbc-*/build.gradle.kts`（`archiveFileName=app.jar`） |
| 2 打后端镜像 | `COPY app.jar` + `eclipse-temurin:21.0.12_8-jre` | 各 `dbc-*/Dockerfile`；由 `deploy/apps/docker-compose.yml` 的 `build:` 触发 |
| 3 打包并打前端镜像 | Dockerfile 多阶段 `npm run build` | `dbc-front/Dockerfile`；`compose` 服务 `dbc-front` |
| 4 运行 | `compose up` | `deploy/middleware` + `deploy/apps` |

**注意**：运行中的前端以 **镜像内静态资源** 为准；工作区 `front/html` 仅便于本机查看，默认不再挂进容器（避免空目录覆盖镜像）。Nginx 配置仍可挂载 `front/conf/default.conf`。

---

## 5. 一键构建与启动

### 5.1 前置

1. Docker Desktop 已启动（建议内存 ≥ 8GB）。  
2. 释放本机已占用的 5432 / 6379 / 8000 / 9200 等端口。  
3. 安装 JDK 21、Node 18+（打包机需要；前端亦可仅在 Docker 构建阶段用 Node 镜像）。

### 5.2 构建 Jar（+ 可选前端落盘）

```powershell
cd e:\workspace\database-client
powershell -ExecutionPolicy Bypass -File .\scripts\build-docker-apps.ps1
```

### 5.3 启动中间件

```powershell
docker compose -f deploy/middleware/docker-compose.yml up -d
docker compose -f deploy/middleware/docker-compose.yml ps
```

检查：

```powershell
docker exec dbc-postgres pg_isready -U postgres
docker exec dbc-redis redis-cli ping
curl.exe -s http://127.0.0.1:9200
curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8000/nacos/v1/ns/operator/metrics
```

Nacos 控制台：`http://127.0.0.1:8001/nacos`（Nacos 3.x）。

### 5.4 制作应用镜像并启动

```powershell
docker compose -f deploy/apps/docker-compose.yml up -d --build
docker compose -f deploy/apps/docker-compose.yml ps
```

浏览器：`http://127.0.0.1:8080`  
账号：`admin` / `admin`（以 Flyway 初始化为准）

### 5.5 停止

```powershell
docker compose -f deploy/apps/docker-compose.yml down
docker compose -f deploy/middleware/docker-compose.yml down
# 数据在 E:\app\docker\workspace\dbc\** ，down 默认不删宿主机目录
```

---

## 6. mTLS 与证书（照做即可）

### 6.1 原则（先看这三句）

1. Docker **不会每次启动都重签**；目录里已有 `server.p12` 就继续用。  
2. 新证书 SAN 同时包含 `localhost` / `127.0.0.1` 和 `dbc-usercenter` / `dbc-audit`，**本机 IDEA 与 Docker 共用一套 secrets**。  
3. 从本机迁到 Docker 的**第一次**：删掉旧 `server.p12` / `server.pass`，让 usercenter 生成新证，再同步回仓库。

### 6.2 第一次上 Docker（必做）

在仓库根执行：

```powershell
cd E:\workspace\database-client

# 1) 删旧服务端证书（工作区 + 仓库都删，避免旧文件被同步回来）
Remove-Item -Force "E:\app\docker\workspace\dbc\secrets\mtls\server.p12" -ErrorAction SilentlyContinue
Remove-Item -Force "E:\app\docker\workspace\dbc\secrets\mtls\server.pass" -ErrorAction SilentlyContinue
Remove-Item -Force "E:\workspace\database-client\secrets\mtls\server.p12" -ErrorAction SilentlyContinue
Remove-Item -Force "E:\workspace\database-client\secrets\mtls\server.pass" -ErrorAction SilentlyContinue

# 2) 先起 usercenter（自动生成新证书；需中间件已 up，Jar 已打好）
docker compose -f deploy/apps/docker-compose.yml up -d --build dbc-usercenter

# 等 1～2 分钟后，确认证书目录有文件
dir E:\app\docker\workspace\dbc\secrets\mtls\

# 3) 再起全部应用
docker compose -f deploy/apps/docker-compose.yml up -d --build

# 4) 同步回仓库（以后 IDEA 本机跑也用这套证）
robocopy "E:\app\docker\workspace\dbc\secrets" "E:\workspace\database-client\secrets" /E
```

### 6.3 以后怎么做

| 场景 | 你要做的 |
| --- | --- |
| 只跑 Docker | 不用再删证书，直接 `compose up` |
| IDEA 本机跑 | 用仓库 `secrets/`（上面第 4 步已同步） |
| mTLS 又报错 / 证书坏了 | 再从 **6.2** 第 1 步删证书重做一遍 |

容器内业务互调**不**写死容器名端口，统一经 Nacos：

| 类型 | 配置形态 | 解析 |
| --- | --- | --- |
| HTTP | `http://dbc-usercenter`（无端口） | `@LoadBalanced RestClient` |
| mTLS | `discovery://dbc-usercenter` | Nacos 选实例 + metadata `mtls-port` |

本地排障可用绝对地址逃生舱（如 `https://127.0.0.1:8044`）。

---

## 7. 配置如何进容器

业务默认走 Nacos 服务名 / `discovery://`；Docker 下由 Compose 注入（亦可省略，与 jar 内默认一致）：

| 变量 | 容器内示例 |
| --- | --- |
| `DBC_NACOS_ADDR` | `nacos:8848` |
| `DBC_DB_URL` | `jdbc:postgresql://postgres:5432/postgres?currentSchema=...` |
| `DBC_REDIS_HOST` | `redis` |
| `DBC_ES_URIS` | `http://elasticsearch:9200` |
| `DBC_SECRETS_DIR` | `/app/secrets` |
| `DBC_USERCENTER_BASE_URL` | `http://dbc-usercenter`（LoadBalancer） |
| `DBC_USERCENTER_MTLS_BASE_URL` / `DBC_AUDIT_MTLS_BASE_URL` | `discovery://dbc-*`（**其它服务**调对方） |
| `DBC_MTLS_BASE_URL` | **仅 usercenter**：`https://127.0.0.1:8044` 本机回环代签 |
| `DBC_MANAGE_BASE_URL` / `DBC_SQLWORK_BASE_URL` | `http://dbc-manage` / `http://dbc-sqlwork` |

`sqlwork` 学习环境 **单实例**（会话与目标库连接池在进程内）。

---

## 8. 文件索引

| 路径 | 说明 |
| --- | --- |
| `deploy/middleware/docker-compose.yml` | 中间件 |
| `deploy/apps/docker-compose.yml` | 前后端 |
| `deploy/apps/nginx/default.conf` | 前端反代模板（同步到工作区） |
| `dbc-*/Dockerfile` | Java 服务镜像（基础：`eclipse-temurin:21.0.12_8-jre`） |
| `dbc-front/Dockerfile` | 前端多阶段构建（`node:26.8.2-slim` → `nginx:stable-alpine`） |
| `scripts/init-docker-workspace.ps1` | 建目录 / 同步 conf、secrets |
| `scripts/build-docker-apps.ps1` | 仅打包 Jar（被 deploy 调用） |
| `scripts/docker-deploy.ps1` / `docker-deploy.cmd` | **一键部署/启动**（请用 `.cmd`） |
| `scripts/docker-stop.ps1` / `docker-stop.cmd` | **一键停止**（请用 `.cmd`） |
| [01-本地启动说明.md](./01-本地启动说明.md) | 非 Docker 的本机启动 |

---

## 9. 故障排查

| 现象 | 处理 |
| --- | --- |
| 端口占用 | 停本机 PG/Redis/Nacos/ES 或改映射 |
| front 打开空白 | 确认 `compose build dbc-front` 成功；或看容器内 `/usr/share/nginx/html` |
| 注册 Nacos 失败 | 中间件是否在 `dbc-net`；地址应为 `nacos:8848` |
| mTLS / 握手失败 | 按 §6 重签 `server.p12` |
| audit 不可用 | ES 未就绪或 `9200` 不通 |
| ES 启动失败 | Docker 内存不够；或清 `elasticsearch\data` 后重试（会丢审计索引） |
| 找不到 app.jar | 先跑 `build-docker-apps.ps1`；并确认 `.dockerignore` 未排除 `build/libs/app.jar` |
| postgres Restarting / PG18 数据目录报错 | 挂载须为 `/var/lib/postgresql`；学习环境可清空 `E:\app\docker\workspace\dbc\postgres\data` 后重起中间件 |

---

## 10. 操作步骤总结

### 10.0 一键脚本（推荐，直接用这个）

在仓库根目录执行。**用 `.cmd`，不要只敲 `.ps1` 文件名。**

```powershell
cd E:\workspace\database-client

# 日常启动
.\scripts\docker-deploy.cmd

# 改过代码
.\scripts\docker-deploy.cmd -Build

# 首次 / 大刷新
.\scripts\docker-deploy.cmd -Full

# 停止
.\scripts\docker-stop.cmd
```

`.cmd` 会自动带上 `-ExecutionPolicy Bypass` 调用对应 `.ps1`，在 Cursor 终端、Windows Terminal、CMD 里都能跑。

默认行为（可反复执行）：

- 不 `down` 已有栈，只 `up -d` 保证起来  
- 不杀本机端口（避免误杀 IDEA / 本机服务）  
- 已有 `app.jar` 则不重新打包  
- 已有 `dbc-*:0.1.0` 镜像则不 `--build`  
- 已有 mTLS 标记/证书则不重签  
- 不自动清空 Postgres 数据  

可选参数：

| 参数 | 何时用 |
| --- | --- |
| （无参数） | 每天启动 / 停掉后再拉起 |
| `-Build` | 改了后端/前端代码，要重新打 Jar 并重建镜像 |
| `-RebuildImages` | Jar 已有，只强制 `compose --build` |
| `-RenewMtls` | 证书有问题，强制重签 |
| `-FreePorts` | 端口被本机进程占用，需要清掉 |
| `-ResetPostgres` | PG 起不来，允许清空本地 PG 数据后重试 |
| `-Full` | 首次或大刷新：down + FreePorts + Build + RebuildImages +（首次）RenewMtls + ResetPostgres |
| `docker-stop.cmd -WipeData` | 停止并清空中间件数据（会丢库） |

成功后打开：`http://127.0.0.1:8080`，账号 `admin` / `admin`。  
Nacos：`http://127.0.0.1:8001/nacos`。

> 下面分步说明仅供排障；平时用 10.0 即可。

### 10.1 PowerShell 禁止运行脚本

统一加 Bypass（仅本次进程，不改系统策略）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\xxx.ps1
```

若希望以后直接敲 `.\scripts\xxx.ps1`，可执行一次：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 第一步：确认基础镜像已在本地（断网必做）

```powershell
docker images
# 应能看到：
#   postgres:18
#   redis:8.8.2
#   nacos/nacos-server:v3.2.4-slim
#   elasticsearch:9.2.3
#   eclipse-temurin:21.0.12_8-jre
#   node:26.8.2-slim
#   nginx:stable-alpine
```

缺哪个就在有网时 `docker pull <镜像>`（完整清单见 §1.1）。

### 第二步：停掉本机冲突进程

需空出端口：`5432`、`6379`、`8000`、`8001`、`9000`、`9200`、`8003`～`8008`、`8044`、`8048`、`8080`。

#### 2.1 若以前起过本仓库的 Compose，先停容器

```powershell
cd e:\workspace\database-client
docker compose -f deploy/apps/docker-compose.yml down
docker compose -f deploy/middleware/docker-compose.yml down
```

#### 2.2 查看哪些端口仍被占用

```powershell
$ports = 5432,6379,8000,8001,8003,8004,8005,8006,8007,8008,8044,8048,8080,9000,9200
foreach ($p in $ports) {
  $owns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
  if ($owns) {
    foreach ($procId in $owns) {
      $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
      Write-Host "端口 $p -> PID $procId ($($proc.ProcessName))"
    }
  }
}
```

无输出表示这些端口当前空闲。

#### 2.3 结束占用端口的进程（确认 PID 后再杀）

单个端口示例（把 `5432` 换成实际冲突端口）：

```powershell
Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force }
```

一次清掉上述全部端口（**会强制结束监听这些端口的进程**，含本机 PostgreSQL / Redis / 旧 Nacos / IDEA 起的 Java 等）：

```powershell
$ports = 5432,6379,8000,8001,8003,8004,8005,8006,8007,8008,8044,8048,8080,9000,9200
foreach ($p in $ports) {
  Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object {
      Write-Host "停止 PID $_ (端口 $p)"
      Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
}
```

#### 2.4 其它需手动停的

| 来源 | 怎么停 |
| --- | --- |
| IDEA / `gradlew bootRun` | IDE 停止按钮，或结束对应 `java` 进程 |
| 本机 Nacos（`startup.cmd`） | 到 Nacos 安装目录执行 `shutdown.cmd`，或结束 `nacos`/`java` |
| Windows 服务装的 PostgreSQL/Redis | `services.msc` 停服务，或 `Stop-Service` |
| Vite 前端 `:8005` | 关掉对应终端 / 结束 `node` |

停完再跑一遍 **2.2**，确认无占用后再进入第三步。

### 第三步：初始化宿主机目录

```powershell
cd e:\workspace\database-client
powershell -ExecutionPolicy Bypass -File .\scripts\init-docker-workspace.ps1
```

会创建 `E:\app\docker\workspace\dbc\...`，并同步 nginx 配置与（若有）`secrets`。

### 第四步：打包后端 Jar

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-docker-apps.ps1
```

产出：各 `dbc-*\build\libs\app.jar`。  
脚本也可能在本机 npm 构建前端并同步到工作区便于查看；**真正进容器的前端仍由 `dbc-front/Dockerfile` 在镜像构建时打包**。

### 第五步：启动中间件

```powershell
docker compose -f deploy/middleware/docker-compose.yml up -d
docker compose -f deploy/middleware/docker-compose.yml ps
```

自检：

```powershell
docker exec dbc-postgres pg_isready -U postgres
docker exec dbc-redis redis-cli ping
curl.exe -s http://127.0.0.1:9200
curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8000/nacos/v1/ns/operator/metrics
```

Nacos 控制台：`http://127.0.0.1:8001/nacos`

### 第六步：处理 mTLS 证书（第一次上 Docker 必做；日常可跳过）

> 详情见上文 **§6**。这里直接复制命令。

```powershell
cd E:\workspace\database-client

# 删旧证书
Remove-Item -Force "E:\app\docker\workspace\dbc\secrets\mtls\server.p12" -ErrorAction SilentlyContinue
Remove-Item -Force "E:\app\docker\workspace\dbc\secrets\mtls\server.pass" -ErrorAction SilentlyContinue
Remove-Item -Force "E:\workspace\database-client\secrets\mtls\server.p12" -ErrorAction SilentlyContinue
Remove-Item -Force "E:\workspace\database-client\secrets\mtls\server.pass" -ErrorAction SilentlyContinue

# 先起 usercenter，生成新证书（等 1～2 分钟）
docker compose -f deploy/apps/docker-compose.yml up -d --build dbc-usercenter
dir E:\app\docker\workspace\dbc\secrets\mtls\
```

证书出来后再做第七步。  
**以后**日常重启不用再删证书；只有 mTLS 失败时才重做本步。

### 第七步：启动其余前后端

```powershell
cd E:\workspace\database-client
docker compose -f deploy/apps/docker-compose.yml up -d --build
docker compose -f deploy/apps/docker-compose.yml ps

# 同步证书回仓库，方便以后 IDEA 本机跑
robocopy "E:\app\docker\workspace\dbc\secrets" "E:\workspace\database-client\secrets" /E
```

### 第八步：验证

1. 浏览器打开：`http://127.0.0.1:8080`  
2. 登录：`admin` / `admin`（以库初始化为准）  
3. Nacos（`http://127.0.0.1:8001/nacos`）中应看到 gateway / usercenter / manage / sqlwork / audit  

### 日常重启 / 停机

```powershell
# 只重启应用（不改镜像、不删证书）
docker compose -f deploy/apps/docker-compose.yml restart

# 代码变更后：重新打包 → 重建镜像并启动
powershell -ExecutionPolicy Bypass -File .\scripts\build-docker-apps.ps1
docker compose -f deploy/apps/docker-compose.yml up -d --build

# 全部停止（数据仍在 E:\app\docker\workspace\dbc）
docker compose -f deploy/apps/docker-compose.yml down
docker compose -f deploy/middleware/docker-compose.yml down
```

### 流程一句话

```text
每天启动：  .\scripts\docker-deploy.cmd
改代码：    .\scripts\docker-deploy.cmd -Build
首次/大刷： .\scripts\docker-deploy.cmd -Full
停止：      .\scripts\docker-stop.cmd
```
