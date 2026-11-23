-- V1 种子把 path 写成了 /METADATA 等编码，detail 组装 categoryPath 时 Long.parseLong 失败。
-- 统一修正为 /{id}；已是数字 path 的不动。

UPDATE knowledge.t_knowledge_category
SET path = '/' || id::text,
    updated_at = NOW()
WHERE path IS NULL
   OR path = ''
   OR path ~ '[^0-9/]';
