plugins {
    `java-library`
}

dependencies {
    api(project(":dbc-client-common"))
    compileOnly("org.springframework.boot:spring-boot-autoconfigure:3.3.5")
    compileOnly("org.springframework:spring-web:6.1.14")
    compileOnly("org.springframework:spring-context:6.1.14")
    compileOnly("org.springframework:spring-aop:6.1.14")
    compileOnly("org.springframework:spring-expression:6.1.14")
    compileOnly("org.springframework.security:spring-security-core:6.3.4")
    compileOnly("org.aspectj:aspectjweaver:1.9.22.1")
    compileOnly("jakarta.servlet:jakarta.servlet-api:6.0.0")
    compileOnly("com.fasterxml.jackson.core:jackson-databind:2.17.2")
    compileOnly("org.slf4j:slf4j-api:2.0.16")
    compileOnly("org.projectlombok:lombok:1.18.34")
    annotationProcessor("org.projectlombok:lombok:1.18.34")

    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
    testImplementation("org.mockito:mockito-core:5.12.0")
    testImplementation("org.mockito:mockito-junit-jupiter:5.12.0")
    testImplementation("org.assertj:assertj-core:3.26.3")
    testImplementation("com.fasterxml.jackson.core:jackson-databind:2.17.2")
    testImplementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310:2.17.2")
    testImplementation("org.springframework:spring-aop:6.1.14")
    testImplementation("org.springframework:spring-context:6.1.14")
    testImplementation("org.springframework:spring-expression:6.1.14")
    testImplementation("org.springframework:spring-core:6.1.14")
    testImplementation("org.springframework:spring-beans:6.1.14")
    testImplementation("org.springframework.security:spring-security-core:6.3.4")
    testImplementation("org.aspectj:aspectjweaver:1.9.22.1")
    testImplementation("jakarta.servlet:jakarta.servlet-api:6.0.0")
    testImplementation("org.slf4j:slf4j-api:2.0.16")
    testRuntimeOnly("org.slf4j:slf4j-simple:2.0.16")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher:1.10.2")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
