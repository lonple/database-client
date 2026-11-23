package com.lyj.dbc.knowledge.llm.client;

import com.lyj.dbc.knowledge.llm.config.LlmProperties;
import com.lyj.dbc.knowledge.llm.error.LlmException;
import com.lyj.dbc.knowledge.llm.meter.LlmMeter;
import com.lyj.dbc.knowledge.llm.model.ChatMessage;
import com.lyj.dbc.knowledge.llm.model.ChatRequest;
import com.lyj.dbc.knowledge.llm.model.ChatResponse;
import com.lyj.dbc.knowledge.llm.model.LlmToolCall;
import com.lyj.dbc.knowledge.llm.model.RerankHit;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.ToolResponseMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.ai.embedding.EmbeddingOptions;
import org.springframework.ai.embedding.EmbeddingRequest;
import org.springframework.ai.embedding.EmbeddingResponse;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * 基于 Spring AI OpenAI 兼容客户端（默认通义千问；也可改 base-url 对接 DeepSeek 等）。
 */
public class SpringAiLlmClient implements LlmClient {
    private final ChatModel chatModel;
    private final EmbeddingModel embeddingModel;
    private final LlmProperties properties;
    private final LlmMeter meter;
    private final DashScopeRerankClient rerankClient;

    public SpringAiLlmClient(ChatModel chatModel,
                             EmbeddingModel embeddingModel,
                             LlmProperties properties,
                             LlmMeter meter) {
        this.chatModel = chatModel;
        this.embeddingModel = embeddingModel;
        this.properties = properties;
        this.meter = meter;
        this.rerankClient = new DashScopeRerankClient(properties);
    }

    @Override
    public ChatResponse chat(ChatRequest request) {
        if (!properties.isEnabled()) {
            throw new LlmException("LLM chat disabled: set dbc.knowledge.llm.enabled=true and dbc.knowledge.llm.api-key");
        }
        long start = System.currentTimeMillis();
        boolean ok = false;
        Integer promptTokens = null;
        Integer completionTokens = null;
        try {
            List<Message> messages = new ArrayList<>();
            for (ChatMessage m : request.getMessages()) {
                messages.add(toSpringMessage(m));
            }
            String model = StringUtils.hasText(request.getModel()) ? request.getModel() : properties.getChatModel();
            OpenAiChatOptions.Builder opt = OpenAiChatOptions.builder();
            if (StringUtils.hasText(model)) {
                opt.model(model);
            }
            if (request.getTemperature() != null) {
                opt.temperature(request.getTemperature());
            }
            if (request.getMaxTokens() != null) {
                opt.maxTokens(request.getMaxTokens());
            }
            List<ToolCallback> toolCallbacks = resolveToolCallbacks(request.getToolObjects());
            if (!toolCallbacks.isEmpty()) {
                opt.toolCallbacks(toolCallbacks);
                // 由业务侧执行工具（便于记 trace / 控制多轮），这里只把 @Tool schema 交给模型
                opt.internalToolExecutionEnabled(false);
            }
            Prompt prompt = new Prompt(messages, opt.build());
            org.springframework.ai.chat.model.ChatResponse aiResp = chatModel.call(prompt);
            String content = "";
            List<LlmToolCall> toolCalls = new ArrayList<>();
            if (aiResp != null && aiResp.getResult() != null && aiResp.getResult().getOutput() != null) {
                AssistantMessage out = aiResp.getResult().getOutput();
                content = out.getText() == null ? "" : out.getText();
                if (out.hasToolCalls()) {
                    for (AssistantMessage.ToolCall tc : out.getToolCalls()) {
                        toolCalls.add(LlmToolCall.builder()
                                .id(tc.id())
                                .name(tc.name())
                                .arguments(tc.arguments())
                                .build());
                    }
                }
            }
            if (aiResp != null && aiResp.getMetadata() != null && aiResp.getMetadata().getUsage() != null) {
                var usage = aiResp.getMetadata().getUsage();
                promptTokens = usage.getPromptTokens() == null ? null : usage.getPromptTokens().intValue();
                completionTokens = usage.getCompletionTokens() == null ? null : usage.getCompletionTokens().intValue();
            }
            ok = true;
            return ChatResponse.builder()
                    .content(content == null ? "" : content)
                    .toolCalls(toolCalls)
                    .promptTokens(promptTokens)
                    .completionTokens(completionTokens)
                    .model(model)
                    .build();
        } catch (LlmException e) {
            throw e;
        } catch (Exception e) {
            throw new LlmException("LLM chat failed: " + e.getMessage(), e);
        } finally {
            meter.record("chat", request.getCaller(), promptTokens, completionTokens,
                    System.currentTimeMillis() - start, ok);
        }
    }

    /**
     * 支持：{@code @Tool} 实例（MethodToolCallbackProvider）、已有 {@link ToolCallback}。
     */
    static List<ToolCallback> resolveToolCallbacks(List<Object> toolObjects) {
        if (toolObjects == null || toolObjects.isEmpty()) {
            return List.of();
        }
        List<ToolCallback> direct = new ArrayList<>();
        List<Object> annotated = new ArrayList<>();
        for (Object o : toolObjects) {
            if (o == null) {
                continue;
            }
            if (o instanceof ToolCallback cb) {
                direct.add(cb);
            } else if (o instanceof ToolCallback[] arr) {
                direct.addAll(Arrays.asList(arr));
            } else {
                annotated.add(o);
            }
        }
        if (!annotated.isEmpty()) {
            ToolCallback[] fromMethods = MethodToolCallbackProvider.builder()
                    .toolObjects(annotated.toArray())
                    .build()
                    .getToolCallbacks();
            direct.addAll(Arrays.asList(fromMethods));
        }
        return direct;
    }

    @Override
    public float[] embed(String text) {
        return embed(List.of(text == null ? "" : text)).get(0);
    }

    @Override
    public List<float[]> embed(List<String> texts) {
        if (texts == null || texts.isEmpty()) {
            return List.of();
        }
        if (!properties.isEnabled() || embeddingModel == null || !properties.isEmbedEnabled()) {
            return stubEmbed(texts);
        }
        long start = System.currentTimeMillis();
        boolean ok = false;
        Integer promptTokens = null;
        try {
            EmbeddingOptions.Builder opt = EmbeddingOptions.builder();
            if (StringUtils.hasText(properties.getEmbedModel())) {
                opt.model(properties.getEmbedModel());
            }
            EmbeddingRequest req = new EmbeddingRequest(texts, opt.build());
            EmbeddingResponse resp = embeddingModel.call(req);
            if (resp.getMetadata() != null && resp.getMetadata().getUsage() != null
                    && resp.getMetadata().getUsage().getPromptTokens() != null) {
                promptTokens = resp.getMetadata().getUsage().getPromptTokens().intValue();
            }
            List<float[]> out = new ArrayList<>();
            resp.getResults().forEach(r -> {
                float[] vec = r.getOutput();
                out.add(resize(vec, properties.getEmbedDim()));
            });
            ok = true;
            return out;
        } catch (Exception e) {
            throw new LlmException("LLM embed failed: " + e.getMessage(), e);
        } finally {
            meter.record("embed", "core", promptTokens, null,
                    System.currentTimeMillis() - start, ok);
        }
    }

    @Override
    public List<RerankHit> rerank(String query, List<String> documents) {
        if (documents == null || documents.isEmpty()) {
            return List.of();
        }
        if (!properties.isEnabled() || !properties.isRerankEnabled()) {
            return StubLlmClient.identityRerank(documents);
        }
        long start = System.currentTimeMillis();
        boolean ok = false;
        try {
            List<RerankHit> hits = rerankClient.rerank(query, documents);
            ok = true;
            return hits;
        } catch (LlmException e) {
            throw e;
        } catch (Exception e) {
            throw new LlmException("LLM rerank failed: " + e.getMessage(), e);
        } finally {
            meter.record("rerank", "core", null, null,
                    System.currentTimeMillis() - start, ok);
        }
    }

    private Message toSpringMessage(ChatMessage m) {
        String role = m.getRole() == null ? "user" : m.getRole().toLowerCase();
        String content = m.getContent() == null ? "" : m.getContent();
        return switch (role) {
            case "system" -> new SystemMessage(content);
            case "assistant" -> {
                if (m.getToolCalls() != null && !m.getToolCalls().isEmpty()) {
                    List<AssistantMessage.ToolCall> calls = new ArrayList<>();
                    for (LlmToolCall tc : m.getToolCalls()) {
                        calls.add(new AssistantMessage.ToolCall(
                                tc.getId() == null ? "" : tc.getId(),
                                "function",
                                tc.getName() == null ? "" : tc.getName(),
                                tc.getArguments() == null ? "{}" : tc.getArguments()));
                    }
                    yield AssistantMessage.builder().content(content).toolCalls(calls).build();
                }
                yield new AssistantMessage(content);
            }
            case "tool" -> ToolResponseMessage.builder()
                    .responses(List.of(new ToolResponseMessage.ToolResponse(
                            m.getToolCallId() == null ? "" : m.getToolCallId(),
                            m.getName() == null ? "" : m.getName(),
                            content)))
                    .build();
            default -> new UserMessage(content);
        };
    }

    private List<float[]> stubEmbed(List<String> texts) {
        int dim = Math.max(8, properties.getEmbedDim());
        List<float[]> out = new ArrayList<>();
        for (String t : texts) {
            float[] v = new float[dim];
            int h = t == null ? 0 : t.hashCode();
            for (int i = 0; i < dim; i++) {
                v[i] = ((h >> (i % 24)) & 0xff) / 255f;
            }
            out.add(v);
        }
        return out;
    }

    private static float[] resize(float[] vec, int dim) {
        if (vec == null) {
            return new float[dim];
        }
        if (vec.length == dim) {
            return vec;
        }
        float[] resized = new float[dim];
        System.arraycopy(vec, 0, resized, 0, Math.min(vec.length, dim));
        return resized;
    }
}
