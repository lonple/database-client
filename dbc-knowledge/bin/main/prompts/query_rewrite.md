# Query rewrite for knowledge vector search

Product name (DB filter only; do NOT put into topicQuery): {{productName}}
User question (raw):
{{query}}

Task:
Rewrite for dual-path retrieval:
- Document dense vectors: original title + intro/summary
- Slice dense vectors: slice title + description + body summary
- Slice full-text (BM25): slice body only

Rules:
1. Do NOT answer the question. Only rewrite for search.
2. Do NOT invent product features or facts not implied by the question.
3. topicQuery: 8–40 Chinese characters (or short English). Noun-phrase like a title/description/summary,
   e.g. 「一次性项目预算」「总体技术架构」「mTLS 双向认证」. No product name prefix. No chat filler.
4. bodyQuery / keywords: terms useful for matching technical body text (APIs, configs, error phrases).
5. Prefer team domain terms over casual synonyms when both appear.

Reply JSON only:
{"topicQuery":"","bodyQuery":"","keywords":""}
