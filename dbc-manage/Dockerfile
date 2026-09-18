# dbc-manage 运行时镜像（先 bootJar → 再 docker build）
# 基础镜像：eclipse-temurin:21.0.12_8-jre
FROM eclipse-temurin:21.0.12_8-jre
WORKDIR /app
RUN mkdir -p /app/secrets /app/logs /app/secrets/manage/drivers
COPY build/libs/app.jar /app/app.jar
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75.0"
EXPOSE 8006
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
