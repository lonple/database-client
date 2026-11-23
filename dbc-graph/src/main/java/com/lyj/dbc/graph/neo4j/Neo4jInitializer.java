package com.lyj.dbc.graph.neo4j;

import org.neo4j.driver.Driver;
import org.neo4j.driver.Session;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

@Component
@Order(1)
public class Neo4jInitializer implements ApplicationRunner {
    private static final Logger log = LoggerFactory.getLogger(Neo4jInitializer.class);

    private final Driver driver;

    public Neo4jInitializer(Driver driver) {
        this.driver = driver;
    }

    @Override
    public void run(ApplicationArguments args) {
        try (Session session = driver.session()) {
            session.run("""
                    CREATE CONSTRAINT kg_node_uniq IF NOT EXISTS
                    FOR (n:KgNode) REQUIRE (n.graphId, n.nodeId) IS UNIQUE
                    """);
            session.run("""
                    CREATE INDEX kg_node_name IF NOT EXISTS
                    FOR (n:KgNode) ON (n.graphId, n.name)
                    """);
            log.info("Neo4j constraints/indexes ready");
        } catch (Exception e) {
            log.warn("Neo4j init skipped or failed: {}", e.getMessage());
        }
    }
}
