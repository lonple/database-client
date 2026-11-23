package com.lyj.dbc.knowledge.llm.client;

import com.lyj.dbc.knowledge.llm.config.LlmProperties;
import com.lyj.dbc.knowledge.llm.error.LlmException;
import com.lyj.dbc.knowledge.llm.meter.LlmMeter;
import com.lyj.dbc.knowledge.llm.model.ChatRequest;
import com.lyj.dbc.knowledge.llm.model.ChatResponse;
import com.lyj.dbc.knowledge.llm.model.RerankHit;

import java.util.ArrayList;
import java.util.List;

/** 未启用真实 LLM 或缺少 api-key 时的占位：chat 拒绝，embed 本地 stub。 */
public class StubLlmClient implements LlmClient {
    private final LlmProperties properties;
    private final LlmMeter meter;

    public StubLlmClient(LlmProperties properties, LlmMeter meter) {
        this.properties = properties;
        this.meter = meter;
    }

    @Override
    public ChatResponse chat(ChatRequest request) {
        meter.record("chat", request.getCaller(), null, null, 0, false);
        throw new LlmException("LLM chat disabled: set dbc.knowledge.llm.enabled=true and dbc.knowledge.llm.api-key");
    }

    @Override
    public float[] embed(String text) {
        return embed(List.of(text == null ? "" : text)).get(0);
    }

    @Override
    public List<float[]> embed(List<String> texts) {
        long start = System.currentTimeMillis();
        int dim = Math.max(8, properties.getEmbedDim());
        List<float[]> out = new ArrayList<>();
        for (String t : texts == null ? List.<String>of() : texts) {
            float[] v = new float[dim];
            int h = t == null ? 0 : t.hashCode();
            for (int i = 0; i < dim; i++) {
                v[i] = ((h >> (i % 24)) & 0xff) / 255f;
            }
            out.add(v);
        }
        meter.record("embed", "stub", null, null, System.currentTimeMillis() - start, true);
        return out;
    }

    @Override
    public List<RerankHit> rerank(String query, List<String> documents) {
        long start = System.currentTimeMillis();
        List<RerankHit> out = identityRerank(documents);
        meter.record("rerank", "stub", null, null, System.currentTimeMillis() - start, true);
        return out;
    }

    static List<RerankHit> identityRerank(List<String> documents) {
        if (documents == null || documents.isEmpty()) {
            return List.of();
        }
        List<RerankHit> out = new ArrayList<>(documents.size());
        int n = documents.size();
        for (int i = 0; i < n; i++) {
            out.add(new RerankHit(i, n - i));
        }
        return out;
    }
}
