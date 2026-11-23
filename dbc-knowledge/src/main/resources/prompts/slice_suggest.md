# Slice suggest — Qwen3b-RagSemanticChunker

Runtime model: `ada.llm.slice-model` (default `Qwen3b-RagSemanticChunker`).
Query rewrite and category recommend stay on `ada.llm.chat-model`.

System:
Your job is to act as a semantic chunker.
The goal is to separate the content into semantically relevant groupings.
Each group must be delimited by the "段" character.

User:
Segment this text:

```text
{{body}}
```

Optional caller slice rule is appended to the system message.
The service splits the reply on 「段」 and stores each group as one slice:
- title: first heading / first non-blank line (truncated)
- description: 1st non-blank line of the segment body
- bodySummary: 2nd non-blank line of the segment body
- body: full segment text
