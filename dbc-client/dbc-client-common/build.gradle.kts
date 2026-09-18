plugins {
    `java-library`
}

dependencies {
    api("com.fasterxml.jackson.core:jackson-databind:2.17.2")
    api("org.springframework:spring-web:6.1.14")
    // 可选：业务服务运行时提供 LoadBalancer / Discovery；本模块仅 compileOnly
    compileOnly("org.springframework.cloud:spring-cloud-commons:4.1.4")
    compileOnly("org.springframework.cloud:spring-cloud-loadbalancer:4.1.4")
    compileOnly("org.springframework:spring-context:6.1.14")
    compileOnly("org.projectlombok:lombok:1.18.34")
    annotationProcessor("org.projectlombok:lombok:1.18.34")
}
