plugins {
    java
}

allprojects {
    group = "com.lyj.dbc"
    version = "0.1.0"

    repositories {
        mavenLocal()
        maven { url = uri("https://maven.aliyun.com/repository/public") }
        mavenCentral()
    }
}

subprojects {
    apply(plugin = "maven-publish")

    tasks.withType<JavaCompile> {
        options.encoding = "UTF-8"
    }

    // 子模块自身已 apply java-library；此处补 sources 与发布到 mavenLocal
    plugins.withId("java") {
        extensions.configure<JavaPluginExtension> {
            sourceCompatibility = JavaVersion.VERSION_21
            targetCompatibility = JavaVersion.VERSION_21
            withSourcesJar()
        }
        extensions.configure<PublishingExtension> {
            publications {
                create<MavenPublication>("mavenJava") {
                    from(components["java"])
                }
            }
        }
    }
}
