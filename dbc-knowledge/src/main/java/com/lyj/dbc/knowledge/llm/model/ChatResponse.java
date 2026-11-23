package com.lyj.dbc.knowledge.llm.model;

import lombok.Builder;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
public class ChatResponse {
    private String content;
    private Integer promptTokens;
    private Integer completionTokens;
    private String model;
    /** 模型发起的 tool_calls；非空时应由调用方执行工具后再带 tool 消息继续聊 */
    @Builder.Default
    private List<LlmToolCall> toolCalls = new ArrayList<>();

    public boolean hasToolCalls() {
        return toolCalls != null && !toolCalls.isEmpty();
    }
}
