package com.lyj.dbc.knowledge.llm.meter;

public interface LlmMeter {
    void record(String operation, String caller, Integer promptTokens, Integer completionTokens,
                long latencyMs, boolean success);
}
