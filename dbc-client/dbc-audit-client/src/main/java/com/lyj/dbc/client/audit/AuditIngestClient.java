package com.lyj.dbc.client.audit;

import com.lyj.dbc.client.audit.dto.AuditEventDtos;
import com.lyj.dbc.client.common.ApiResponse;
import com.lyj.dbc.client.common.MtlsRestClientFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 审计事件异步 HTTP 上报客户端：业务线程只入队，禁止同步等待 ingest。
 */
public class AuditIngestClient implements AuditEventPublisher, AutoCloseable {

    private static final Logger log = LoggerFactory.getLogger(AuditIngestClient.class);

    private final AuditClientProperties properties;
    private final RestClient restClient;
    private final java.util.function.Supplier<String> baseUrlSupplier;
    private final ThreadPoolExecutor executor;
    private final AtomicBoolean closed = new AtomicBoolean(false);
    private final boolean available;

    public AuditIngestClient(AuditClientProperties properties) {
        this(properties, null, null);
    }

    public AuditIngestClient(AuditClientProperties properties,
                             com.lyj.dbc.client.common.DiscoveryHttpsBaseUrlResolver discoveryResolver) {
        this(properties, null, discoveryResolver);
    }

    public AuditIngestClient(AuditClientProperties properties, RestClient restClient) {
        this(properties, restClient, null);
    }

    public AuditIngestClient(AuditClientProperties properties,
                             RestClient restClient,
                             com.lyj.dbc.client.common.DiscoveryHttpsBaseUrlResolver discoveryResolver) {
        this.properties = Objects.requireNonNull(properties, "properties");
        String configured = properties.getMtlsBaseUrl();
        if (discoveryResolver != null) {
            this.baseUrlSupplier = () -> discoveryResolver.resolveHttpsBaseUrl(configured);
        } else {
            String fixed = MtlsRestClientFactory.trimTrailingSlash(configured);
            this.baseUrlSupplier = () -> fixed;
        }
        RestClient client = restClient;
        boolean ok = false;
        if (properties.isEnabled()) {
            if (client == null) {
                try {
                    Path secretsDir = Path.of(properties.getSecretsDir()).toAbsolutePath().normalize();
                    client = MtlsRestClientFactory.create(secretsDir, properties.getClientId());
                    ok = true;
                } catch (Exception e) {
                    log.warn("审计客户端 mTLS 初始化失败，上报将丢弃直至修复: {}", e.getMessage(), e);
                }
            } else {
                ok = true;
            }
        } else {
            log.info("审计客户端已关闭（dbc.audit.client.enabled=false）");
        }
        this.restClient = client;
        this.available = ok;

        int pool = Math.max(1, properties.getAsyncPoolSize());
        int capacity = Math.max(100, properties.getQueueCapacity());
        this.executor = new ThreadPoolExecutor(
                pool, pool,
                60L, TimeUnit.SECONDS,
                new LinkedBlockingQueue<>(capacity),
                new AuditThreadFactory(),
                new ThreadPoolExecutor.AbortPolicy()
        );
        this.executor.allowCoreThreadTimeOut(true);
    }

    public void ingestAsync(AuditEventDtos.AuditEvent event) {
        if (event == null) {
            return;
        }
        List<AuditEventDtos.AuditEvent> one = new ArrayList<>(1);
        one.add(event);
        ingestBatchAsync(one);
    }

    public void ingestBatchAsync(List<AuditEventDtos.AuditEvent> events) {
        if (events == null || events.isEmpty() || closed.get()) {
            return;
        }
        if (!available || restClient == null) {
            log.warn("审计上报跳过：客户端不可用，丢弃 {} 条", events.size());
            return;
        }
        List<AuditEventDtos.AuditEvent> prepared = prepare(events);
        try {
            executor.execute(() -> doSend(prepared));
        } catch (RejectedExecutionException e) {
            log.warn("审计上报队列已满，丢弃 {} 条", prepared.size(), e);
        }
    }

    private List<AuditEventDtos.AuditEvent> prepare(List<AuditEventDtos.AuditEvent> events) {
        List<AuditEventDtos.AuditEvent> out = new ArrayList<>(events.size());
        for (AuditEventDtos.AuditEvent e : events) {
            if (e == null) {
                continue;
            }
            if (e.getEventId() == null || e.getEventId().isBlank()) {
                e.setEventId(UUID.randomUUID().toString());
            }
            if (e.getOccurredAt() == null) {
                e.setOccurredAt(Instant.now());
            }
            if (e.getDetails() != null) {
                e.setDetails(SensitiveFieldFilter.sanitizeMap(e.getDetails()));
            }
            if (e.getFailDetail() != null) {
                e.setFailDetail(SensitiveFieldFilter.sanitizeMap(e.getFailDetail()));
            }
            applySqlCap(e);
            out.add(e);
        }
        return out;
    }

    private void applySqlCap(AuditEventDtos.AuditEvent e) {
        if (e.getSqlText() == null) {
            return;
        }
        int max = Math.max(1024, properties.getSqlMaxBytes());
        byte[] bytes = e.getSqlText().getBytes(StandardCharsets.UTF_8);
        if (bytes.length <= max) {
            if (e.getSqlTruncated() == null) {
                e.setSqlTruncated(false);
            }
            return;
        }
        // 按字节截断，避免半个 UTF-8 字符
        int end = max;
        while (end > 0 && (bytes[end] & 0xC0) == 0x80) {
            end--;
        }
        e.setSqlText(new String(bytes, 0, end, StandardCharsets.UTF_8));
        e.setSqlTruncated(true);
    }

    private void doSend(List<AuditEventDtos.AuditEvent> events) {
        try {
            AuditEventDtos.IngestRequest body = new AuditEventDtos.IngestRequest(events);
            ApiResponse<AuditEventDtos.IngestResult> resp = restClient.post()
                    .uri(baseUrlSupplier.get() + "/inner/events")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(new ParameterizedTypeReference<>() {});
            if (resp == null || !resp.isSuccess()) {
                log.warn("审计上报失败: {}", resp == null ? "空响应" : resp.getMessage());
            }
        } catch (Exception e) {
            log.warn("审计上报失败", e);
        }
    }

    @Override
    public void close() {
        if (!closed.compareAndSet(false, true)) {
            return;
        }
        executor.shutdown();
        try {
            if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            executor.shutdownNow();
        }
    }

    private static final class AuditThreadFactory implements ThreadFactory {
        private final AtomicInteger seq = new AtomicInteger();

        @Override
        public Thread newThread(Runnable r) {
            Thread t = new Thread(r, "dbc-audit-ingest-" + seq.incrementAndGet());
            t.setDaemon(true);
            return t;
        }
    }
}
