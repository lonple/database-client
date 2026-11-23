package com.lyj.dbc.knowledge.llm.model;

import lombok.Builder;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
public class ChatRequest {
    private String model;
    @Builder.Default
    private List<ChatMessage> messages = new ArrayList<>();
    private Double temperature;
    private Integer maxTokens;
    /** Optional: json_object */
    private String responseFormat;
    /** Metering tag only, e.g. memory / review */
    private String caller;
    /**
     * Spring AI 工具对象：带 {@code @Tool} 的实例，或已构造好的 {@code ToolCallback}。
     * schema 由注解/方法签名生成，不写入 system 散文。
     */
    private List<Object> toolObjects;
}
