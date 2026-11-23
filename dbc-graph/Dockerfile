FROM eclipse-temurin:21.0.12_8-jre
WORKDIR /app
RUN mkdir -p /app/secrets /app/logs
COPY build/libs/app.jar /app/app.jar
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75.0"
EXPOSE 8011
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
