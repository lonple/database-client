package com.lyj.dbc.knowledge.knowledge.support;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

class AdaGraphClientTest {
    @Test
    void forwardsCurrentAuthorizationWithoutLeakingToNextRequest() throws Exception {
        AtomicReference<String> authorization = new AtomicReference<>();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/api/graphs/1/table-neighbors", exchange -> {
            authorization.set(exchange.getRequestHeaders().getFirst("Authorization"));
            byte[] body = "{\"data\":{\"neighbors\":[]}}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            try (var output = exchange.getResponseBody()) {
                output.write(body);
            }
        });
        server.start();
        try {
            AdaGraphProperties properties = new AdaGraphProperties();
            properties.setBaseUrl("http://127.0.0.1:" + server.getAddress().getPort());
            AdaGraphClient client = new AdaGraphClient(properties, new ObjectMapper());
            MockHttpServletRequest request = new MockHttpServletRequest();
            request.addHeader("Authorization", "Bearer test-user");
            RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));
            client.tableNeighbors(1, "example", 1, 10);
            assertEquals("Bearer test-user", authorization.get());

            RequestContextHolder.resetRequestAttributes();
            client.tableNeighbors(1, "example", 1, 10);
            assertNull(authorization.get());
        } finally {
            RequestContextHolder.resetRequestAttributes();
            server.stop(0);
        }
    }
}
