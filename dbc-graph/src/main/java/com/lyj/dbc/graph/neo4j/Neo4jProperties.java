package com.lyj.dbc.graph.neo4j;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "dbc.graph.neo4j")
public class Neo4jProperties {
    private String uri = "bolt://127.0.0.1:7687";
    private String username = "neo4j";
    private String password = "changeme";
}
