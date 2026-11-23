package com.lyj.dbc.knowledge.knowledge.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.knowledge.common.api.BizException;
import com.lyj.dbc.knowledge.knowledge.domain.Document;
import com.lyj.dbc.knowledge.knowledge.domain.KnowledgeEnums;
import com.lyj.dbc.knowledge.knowledge.domain.UnitIndex;
import com.lyj.dbc.knowledge.knowledge.domain.VectorSyncEvent;
import com.lyj.dbc.knowledge.knowledge.mapper.DocumentMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.UnitIndexMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.VectorSyncEventMapper;
import com.lyj.dbc.knowledge.knowledge.milvus.MilvusDocumentIndex;
import com.lyj.dbc.knowledge.knowledge.milvus.MilvusProperties;
import com.lyj.dbc.knowledge.knowledge.milvus.MilvusSliceIndex;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.OffsetDateTime;
import java.util.List;

@Service
public class VectorSyncService {
    private static final Logger log = LoggerFactory.getLogger(VectorSyncService.class);

    private final VectorSyncEventMapper eventMapper;
    private final DocumentMapper documentMapper;
    private final UnitIndexMapper unitIndexMapper;
    private final EmbeddingService embeddingService;
    private final ObjectProvider<MilvusSliceIndex> milvusSliceIndex;
    private final ObjectProvider<MilvusDocumentIndex> milvusDocumentIndex;
    private final MilvusProperties milvusProperties;
    private final ObjectProvider<VectorSyncService> self;
    private final TransactionTemplate transactionTemplate;

    public VectorSyncService(VectorSyncEventMapper eventMapper,
                             DocumentMapper documentMapper,
                             UnitIndexMapper unitIndexMapper,
                             EmbeddingService embeddingService,
                             ObjectProvider<MilvusSliceIndex> milvusSliceIndex,
                             ObjectProvider<MilvusDocumentIndex> milvusDocumentIndex,
                             MilvusProperties milvusProperties,
                             ObjectProvider<VectorSyncService> self,
                             TransactionTemplate transactionTemplate) {
        this.eventMapper = eventMapper;
        this.documentMapper = documentMapper;
        this.unitIndexMapper = unitIndexMapper;
        this.embeddingService = embeddingService;
        this.milvusSliceIndex = milvusSliceIndex;
        this.milvusDocumentIndex = milvusDocumentIndex;
        this.milvusProperties = milvusProperties;
        this.self = self;
        this.transactionTemplate = transactionTemplate;
    }

    public void enqueueUpsertAfterCommit(Long documentId) {
        runAfterCommit(() -> {
            Long eventId = self.getObject().enqueue(documentId, VectorSyncEvent.OP_UPSERT);
            self.getObject().processAsync(eventId);
        });
    }

    public void enqueueDeleteAfterCommit(Long documentId) {
        runAfterCommit(() -> {
            Long eventId = self.getObject().enqueue(documentId, VectorSyncEvent.OP_DELETE);
            self.getObject().processAsync(eventId);
        });
    }

    @Transactional
    public Long enqueue(Long documentId, String opType) {
        markDocStatus(documentId, VectorSyncEvent.DOC_SYNC_PENDING);
        VectorSyncEvent event = new VectorSyncEvent();
        event.setDocumentId(documentId);
        event.setOpType(opType);
        event.setStatus(VectorSyncEvent.STATUS_PENDING);
        event.setRetryCount(0);
        event.setMaxRetries(2);
        event.setNextRetryAt(OffsetDateTime.now());
        event.setCreatedAt(OffsetDateTime.now());
        event.setUpdatedAt(OffsetDateTime.now());
        eventMapper.insert(event);
        log.info("vector sync enqueue id={} documentId={} op={}", event.getId(), documentId, opType);
        return event.getId();
    }

    @Transactional
    public Document manualSync(Long documentId) {
        Document doc = documentMapper.selectById(documentId);
        if (doc == null) {
            throw new BizException(404, "原文不存在");
        }
        String op = KnowledgeEnums.STATUS_PUBLISHED.equalsIgnoreCase(doc.getStatus())
                ? VectorSyncEvent.OP_UPSERT
                : VectorSyncEvent.OP_DELETE;
        Long eventId = enqueue(documentId, op);
        self.getObject().processAsync(eventId);
        return documentMapper.selectById(documentId);
    }

    @Async
    public void processAsync(Long eventId) {
        try {
            self.getObject().processOne(eventId);
        } catch (Exception e) {
            log.warn("vector sync async failed eventId={}: {}", eventId, e.getMessage());
        }
    }

    @Scheduled(fixedDelayString = "${dbc.knowledge.milvus.sync-interval-ms:30000}")
    public void compensate() {
        if (!milvusProperties.isEnabled()) {
            return;
        }
        OffsetDateTime now = OffsetDateTime.now();
        List<VectorSyncEvent> due = eventMapper.selectList(new LambdaQueryWrapper<VectorSyncEvent>()
                .eq(VectorSyncEvent::getStatus, VectorSyncEvent.STATUS_PENDING)
                .le(VectorSyncEvent::getNextRetryAt, now)
                .orderByAsc(VectorSyncEvent::getId)
                .last("LIMIT 20"));
        for (VectorSyncEvent e : due) {
            try {
                self.getObject().processOne(e.getId());
            } catch (Exception ex) {
                log.warn("vector sync compensate failed eventId={}: {}", e.getId(), ex.getMessage());
            }
        }
    }

    public void processOne(Long eventId) {
        transactionTemplate.executeWithoutResult(status -> doProcessOne(eventId));
    }

    private void doProcessOne(Long eventId) {
        VectorSyncEvent event = eventMapper.selectById(eventId);
        if (event == null || !VectorSyncEvent.STATUS_PENDING.equals(event.getStatus())) {
            return;
        }
        try {
            execute(event);
            event.setStatus(VectorSyncEvent.STATUS_SUCCESS);
            event.setLastError(null);
            event.setUpdatedAt(OffsetDateTime.now());
            eventMapper.updateById(event);
            String docStatus = VectorSyncEvent.OP_DELETE.equals(event.getOpType())
                    ? VectorSyncEvent.DOC_SYNC_NONE
                    : VectorSyncEvent.DOC_SYNC_SYNCED;
            markDocStatus(event.getDocumentId(), docStatus);
            log.info("vector sync success eventId={} documentId={} op={}", eventId, event.getDocumentId(), event.getOpType());
        } catch (Exception e) {
            handleFailure(event, e);
        }
    }

    private void execute(VectorSyncEvent event) {
        MilvusSliceIndex sliceIndex = milvusSliceIndex.getIfAvailable();
        MilvusDocumentIndex docIndex = milvusDocumentIndex.getIfAvailable();
        if (sliceIndex == null || docIndex == null) {
            throw new IllegalStateException("Milvus 未启用或未连接");
        }
        long documentId = event.getDocumentId();
        if (VectorSyncEvent.OP_DELETE.equals(event.getOpType())) {
            sliceIndex.deleteByDocumentId(documentId);
            docIndex.deleteByDocumentId(documentId);
            return;
        }
        Document doc = documentMapper.selectById(documentId);
        if (doc == null || !KnowledgeEnums.STATUS_PUBLISHED.equalsIgnoreCase(doc.getStatus())) {
            sliceIndex.deleteByDocumentId(documentId);
            docIndex.deleteByDocumentId(documentId);
            return;
        }

        List<UnitIndex> docUnits = unitIndexMapper.selectList(new LambdaQueryWrapper<UnitIndex>()
                .eq(UnitIndex::getKind, KnowledgeEnums.KIND_DOCUMENT)
                .eq(UnitIndex::getRefId, documentId)
                .eq(UnitIndex::getStatus, KnowledgeEnums.STATUS_PUBLISHED));
        List<UnitIndex> slices = unitIndexMapper.selectList(new LambdaQueryWrapper<UnitIndex>()
                .eq(UnitIndex::getDocumentId, documentId)
                .eq(UnitIndex::getKind, KnowledgeEnums.KIND_SLICE)
                .eq(UnitIndex::getStatus, KnowledgeEnums.STATUS_PUBLISHED));

        sliceIndex.deleteByDocumentId(documentId);
        docIndex.deleteByDocumentId(documentId);

        if (!docUnits.isEmpty()) {
            docIndex.upsertDocuments(embeddingService.buildDocumentRows(doc, docUnits));
        }
        if (!slices.isEmpty()) {
            sliceIndex.upsertSlices(embeddingService.buildSliceRows(doc, slices));
        }
    }

    private void handleFailure(VectorSyncEvent event, Exception e) {
        int retry = event.getRetryCount() == null ? 0 : event.getRetryCount();
        int max = event.getMaxRetries() == null ? 2 : event.getMaxRetries();
        String msg = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
        if (msg.length() > 1000) {
            msg = msg.substring(0, 1000);
        }
        if (retry < max) {
            event.setRetryCount(retry + 1);
            event.setStatus(VectorSyncEvent.STATUS_PENDING);
            event.setNextRetryAt(OffsetDateTime.now().plusSeconds(Math.max(1, milvusProperties.getSyncRetryDelayMs() / 1000)));
            event.setLastError(msg);
            event.setUpdatedAt(OffsetDateTime.now());
            eventMapper.updateById(event);
            markDocStatus(event.getDocumentId(), VectorSyncEvent.DOC_SYNC_PENDING);
            log.warn("vector sync retry scheduled eventId={} retry={}/{} err={}",
                    event.getId(), event.getRetryCount(), max, msg);
        } else {
            event.setStatus(VectorSyncEvent.STATUS_FAILED);
            event.setLastError(msg);
            event.setUpdatedAt(OffsetDateTime.now());
            eventMapper.updateById(event);
            markDocStatus(event.getDocumentId(), VectorSyncEvent.DOC_SYNC_UNSYNCED);
            log.error("vector sync stopped after retries eventId={} documentId={} err={}",
                    event.getId(), event.getDocumentId(), msg);
        }
    }

    private void markDocStatus(Long documentId, String status) {
        Document doc = documentMapper.selectById(documentId);
        if (doc == null) {
            return;
        }
        doc.setVectorSyncStatus(status);
        doc.setUpdatedAt(OffsetDateTime.now());
        documentMapper.updateById(doc);
    }

    private void runAfterCommit(Runnable action) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    action.run();
                }
            });
        } else {
            action.run();
        }
    }
}
