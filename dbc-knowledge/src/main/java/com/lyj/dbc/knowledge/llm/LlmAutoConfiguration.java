package com.lyj.dbc.knowledge.llm;

import com.lyj.dbc.knowledge.llm.client.LlmClient;
import com.lyj.dbc.knowledge.llm.client.SpringAiLlmClient;
import com.lyj.dbc.knowledge.llm.client.StubLlmClient;
import com.lyj.dbc.knowledge.llm.config.LlmProperties;
import com.lyj.dbc.knowledge.llm.meter.LlmMeter;
import com.lyj.dbc.knowledge.llm.meter.LoggingLlmMeter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.document.MetadataMode;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.ai.openai.OpenAiChatModel;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.ai.openai.OpenAiEmbeddingModel;
import org.springframework.ai.openai.OpenAiEmbeddingOptions;
import org.springframework.ai.openai.api.OpenAiApi;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;

/**
 * OpenAI 兼容客户端（默认对接通义千问 DashScope compatible-mode；也可改 base-url 接 DeepSeek 等）。
 * 作为本服务内配置类扫描注册（不再依赖独立 jar 的 AutoConfiguration.imports）。
 */
@Configuration
@EnableConfigurationProperties(LlmProperties.class)
public class LlmAutoConfiguration {

    private static final Logger log = LoggerFactory.getLogger(LlmAutoConfiguration.class);

    @Bean
    @ConditionalOnMissingBean
    public LlmMeter llmMeter() {
        return new LoggingLlmMeter();
    }

    @Bean
    @ConditionalOnMissingBean(LlmClient.class)
    @ConditionalOnProperty(prefix = "dbc.knowledge.llm", name = "enabled", havingValue = "true")
    public LlmClient springAiLlmClient(LlmProperties properties, LlmMeter meter) {
        String apiKey = properties.getApiKey() == null ? "" : properties.getApiKey().trim();
        if (!StringUtils.hasText(apiKey)) {
            log.warn("dbc.knowledge.llm.enabled=true but dbc.knowledge.llm.api-key empty; falling back to StubLlmClient. "
                    + "Set dbc.knowledge.llm.api-key or env ADA_LLM_API_KEY.");
            return new StubLlmClient(properties, meter);
        }

        String baseUrl = normalizeOpenAiBaseUrl(StringUtils.hasText(properties.getBaseUrl())
                ? properties.getBaseUrl()
                : "https://dashscope.aliyuncs.com/compatible-mode");

        OpenAiApi chatApi = OpenAiApi.builder()
                .baseUrl(baseUrl)
                .apiKey(apiKey)
                .build();

        OpenAiChatOptions chatOptions = OpenAiChatOptions.builder()
                .model(properties.getChatModel())
                .build();
        ChatModel chatModel = OpenAiChatModel.builder()
                .openAiApi(chatApi)
                .defaultOptions(chatOptions)
                .build();

        EmbeddingModel embeddingModel = null;
        if (properties.isEmbedEnabled()) {
            String embedBase = StringUtils.hasText(properties.getEmbedBaseUrl())
                    ? properties.getEmbedBaseUrl()
                    : properties.getBaseUrl();
            String embedKey = StringUtils.hasText(properties.getEmbedApiKey())
                    ? properties.getEmbedApiKey().trim()
                    : apiKey;
            if (StringUtils.hasText(embedBase) && StringUtils.hasText(embedKey)) {
                OpenAiApi embedApi = OpenAiApi.builder()
                        .baseUrl(normalizeOpenAiBaseUrl(embedBase))
                        .apiKey(embedKey)
                        .build();
                OpenAiEmbeddingOptions.Builder embedOpt = OpenAiEmbeddingOptions.builder()
                        .model(properties.getEmbedModel());
                if (properties.getEmbedDim() > 0) {
                    embedOpt.dimensions(properties.getEmbedDim());
                }
                embeddingModel = new OpenAiEmbeddingModel(embedApi, MetadataMode.EMBED, embedOpt.build());
            } else {
                log.warn("dbc.knowledge.llm.embed-enabled=true but embed base-url/key incomplete; embed will use stub");
            }
        }

        log.info("LLM client ready: chatModel={}, baseUrl={}, embed={}, rerank={} model={}",
                properties.getChatModel(), baseUrl, embeddingModel != null,
                properties.isRerankEnabled(), properties.getRerankModel());
        return new SpringAiLlmClient(chatModel, embeddingModel, properties, meter);
    }

    @Bean
    @ConditionalOnMissingBean(LlmClient.class)
    public LlmClient stubLlmClient(LlmProperties properties, LlmMeter meter) {
        return new StubLlmClient(properties, meter);
    }

    /**
     * Spring AI OpenAiApi 会在 baseUrl 后拼接 /v1/chat/completions；
     * 若配置写成 .../compatible-mode/v1 会变成 .../v1/v1/...，这里去掉末尾 /v1。
     */
    static String normalizeOpenAiBaseUrl(String url) {
        String u = url == null ? "" : url.trim();
        while (u.endsWith("/")) {
            u = u.substring(0, u.length() - 1);
        }
        if (u.endsWith("/v1")) {
            u = u.substring(0, u.length() - 3);
        }
        return u;
    }

}
