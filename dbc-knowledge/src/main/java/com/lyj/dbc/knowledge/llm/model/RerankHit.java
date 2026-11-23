package com.lyj.dbc.knowledge.llm.model;

/**
 * One rerank result. {@code index} is the 0-based position in the input document list.
 */
public record RerankHit(int index, double score) {
}
