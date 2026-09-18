# dbc-client



跨微服务 **inner 客户端** 公共库。调用方依赖对应子模块，通过 mTLS / 后续签名访问对端 `/inner/**`，**不做终端用户功能权限判定**（由对端 inner 过滤器验身份）。



## 模块



| 模块 | 用途 |

| --- | --- |

| `dbc-client-common` | `ApiResponse`、`MtlsRestClientFactory`、异常 |

| `dbc-usercenter-client` | 调 usercenter inner：部门树、权限注册/绑角色等 |

| `dbc-manage-client` | 调 manage inner：空间/连接/鉴权等（供 sqlwork） |

| `dbc-audit-client` | 异步 `AuditIngestClient` + `@AuditLog` AOP + 敏感字段过滤 |



## 本地依赖（推荐，尤其 Windows）



各业务服务默认 **`dbc.client.composite=false`**，从 **mavenLocal** 解析 `com.lyj.dbc:*-client:0.1.0`，启动单个服务时**不会**重打包 `dbc-client` 的 jar，从而避免：



`Unable to delete file ... dbc-xxx-client-0.1.0.jar`（其它 JVM 占用）。



首次或修改本仓库 client 源码后，先发布一次：



```powershell

cd e:\workspace\database-client\scripts

.\publish-dbc-client.ps1

# 或

cd e:\workspace\database-client\dbc-client

.\gradlew.bat publishToMavenLocal

```



业务工程 `build.gradle.kts`：



```kotlin

repositories { mavenLocal(); /* ... */ }

implementation("com.lyj.dbc:dbc-audit-client:0.1.0")

```



### 可选：includeBuild 联调源码



仅在需要改 client 并即时生效、且可停掉其它占用 jar 的服务时使用。在对应服务 `gradle.properties`：



```properties

dbc.client.composite=true

```



## 调用约定



```text

浏览器 → 服务 A（用户 JWT + 功能权限）

       → A 使用 *-client → 服务 B /inner/**（mTLS 或服务签名）

```


