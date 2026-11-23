package com.lyj.dbc.knowledge.llm.meter;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LoggingLlmMeter implements LlmMeter {
    private static final Logger log = LoggerFactory.getLogger(LoggingLlmMeter.class);

    @Override
    public void record(String operation, String caller, Integer promptTokens, Integer completionTokens,
                       long latencyMs, boolean success) {
        log.info("llm op={} caller={} promptTokens={} completionTokens={} latencyMs={} success={}",
                operation, caller, promptTokens, completionTokens, latencyMs, success);
    }
}
