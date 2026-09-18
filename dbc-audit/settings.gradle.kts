rootProject.name = "dbc-audit"

val useCompositeClient: Boolean =
    settings.providers.gradleProperty("dbc.client.composite").orElse("false").map { it.toBoolean() }.get()

if (useCompositeClient) {
    includeBuild("../dbc-client")
}
