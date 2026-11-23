package com.lyj.dbc.graph;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@MapperScan({"com.lyj.dbc.graph.graphmeta.mapper", "com.lyj.dbc.graph.category.mapper"})
@ConfigurationPropertiesScan
public class GraphApplication {
    public static void main(String[] args) {
        SpringApplication.run(GraphApplication.class, args);
    }
}
