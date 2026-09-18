# dbc-audit 运行时镜像（先 bootJar → 再 docker build）
# 基础镜像：eclipse-temurin:21.0.12_8-jre
FROM eclipse-temurin:21.0.12_8-jre
WORKDIR /app
RUN mkdir -p /app/secrets /app/logs
COPY build/libs/app.jar /app/app.jar
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75.0"
# HTTP 查询口 + mTLS ingest 口
EXPOSE 8008 8048
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
