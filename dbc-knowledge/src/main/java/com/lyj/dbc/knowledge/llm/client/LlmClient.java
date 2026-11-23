package com.lyj.dbc.knowledge.llm.client;

import com.lyj.dbc.knowledge.llm.model.ChatRequest;
import com.lyj.dbc.knowledge.llm.model.ChatResponse;
import com.lyj.dbc.knowledge.llm.model.RerankHit;

import java.util.List;

/** Pure model access — no business semantics. */
public interface LlmClient {
    ChatResponse chat(ChatRequest request);

    float[] embed(String text);

    List<float[]> embed(List<String> texts);

    /**
     * Cross-encoder rerank. Returns hits sorted by relevance descending;
     * {@link RerankHit#index()} refers to the input {@code documents} list.
     */
    List<RerankHit> rerank(String query, List<String> documents);
}
