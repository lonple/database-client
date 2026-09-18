plugins {
    `java-library`
}

dependencies {
    api(project(":dbc-client-common"))
    compileOnly("org.projectlombok:lombok:1.18.34")
    annotationProcessor("org.projectlombok:lombok:1.18.34")
}
