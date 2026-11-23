package com.lyj.dbc.knowledge.llm.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ChatMessage {
    private String role;
    private String content;
    /** role=tool 时对应的 tool_call id */
    private String toolCallId;
    /** role=tool 时的工具名 */
    private String name;
    /** role=assistant 且发起工具调用时 */
    private List<LlmToolCall> toolCalls;

    public ChatMessage(String role, String content) {
        this.role = role;
        this.content = content;
    }

    public static ChatMessage system(String content) {
        return new ChatMessage("system", content);
    }

    public static ChatMessage user(String content) {
        return new ChatMessage("user", content);
    }

    public static ChatMessage assistant(String content) {
        return new ChatMessage("assistant", content);
    }

    public static ChatMessage assistantToolCalls(String content, List<LlmToolCall> toolCalls) {
        ChatMessage m = new ChatMessage("assistant", content == null ? "" : content);
        m.setToolCalls(toolCalls);
        return m;
    }

    public static ChatMessage tool(String toolCallId, String toolName, String content) {
        ChatMessage m = new ChatMessage("tool", content == null ? "" : content);
        m.setToolCallId(toolCallId);
        m.setName(toolName);
        return m;
    }
}
