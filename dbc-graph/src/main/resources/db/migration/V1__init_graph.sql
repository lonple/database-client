CREATE SCHEMA IF NOT EXISTS graph;

CREATE TABLE graph.t_graph_category (
    id          BIGSERIAL PRIMARY KEY,
    parent_id   BIGINT NULL REFERENCES graph.t_graph_category(id),
    name        VARCHAR(128) NOT NULL,
    sort_no     INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uk_graph_category_parent_name
    ON graph.t_graph_category (COALESCE(parent_id, 0), name);

CREATE TABLE graph.t_graph (
    id            BIGSERIAL PRIMARY KEY,
    category_id   BIGINT NOT NULL REFERENCES graph.t_graph_category(id),
    code          VARCHAR(64)  NOT NULL,
    name          VARCHAR(256) NOT NULL,
    summary       TEXT NOT NULL,
    product_name  VARCHAR(128) NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uk_graph_code ON graph.t_graph(code);
CREATE INDEX idx_graph_category ON graph.t_graph(category_id);
CREATE INDEX idx_graph_product ON graph.t_graph(product_name);
