# =============================================================================
# dbc-gateway 运行时镜像
# =============================================================================
# 前置：在本模块执行 gradlew bootJar，得到 build/libs/app.jar
#       （通常由 scripts/build-docker-apps.ps1 统一完成）
# 构建：docker compose -f deploy/apps/docker-compose.yml build dbc-gateway
# =============================================================================

# 基础镜像：Adoptium Temurin JRE 21 固定小版本（断网请先 docker pull 同名标签）
FROM eclipse-temurin:21.0.12_8-jre

# 容器内工作目录（与 Compose working_dir、密钥相对路径一致）
WORKDIR /app

# 预创建挂载点（secrets/logs 实际内容由 volume 注入）
RUN mkdir -p /app/secrets /app/logs

# 将宿主机构建产物打进镜像层
COPY build/libs/app.jar /app/app.jar

# JVM 参数：容器内存感知（可被环境变量 JAVA_OPTS 覆盖）
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75.0"

# 声明容器监听端口（文档性；真正发布靠 compose ports）
EXPOSE 8003

# 启动命令
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
