package com.lyj.dbc.knowledge.knowledge.milvus;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "dbc.knowledge.milvus")
public class MilvusProperties {
    private boolean enabled = true;
    private String uri = "http://127.0.0.1:19530";
    private String token = "";
    /** 切片 collection */
    private String collection = "ada_slice";
    /** 原文 collection */
    private String documentCollection = "ada_document";
    private int embedDim = 1024;
    private long syncIntervalMs = 30000;
    private long syncRetryDelayMs = 60000;

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public String getUri() {
        return uri;
    }

    public void setUri(String uri) {
        this.uri = uri;
    }

    public String getToken() {
        return token;
    }

    public void setToken(String token) {
        this.token = token;
    }

    public String getCollection() {
        return collection;
    }

    public void setCollection(String collection) {
        this.collection = collection;
    }

    public String getDocumentCollection() {
        return documentCollection;
    }

    public void setDocumentCollection(String documentCollection) {
        this.documentCollection = documentCollection;
    }

    public int getEmbedDim() {
        return embedDim;
    }

    public void setEmbedDim(int embedDim) {
        this.embedDim = embedDim;
    }

    public long getSyncIntervalMs() {
        return syncIntervalMs;
    }

    public void setSyncIntervalMs(long syncIntervalMs) {
        this.syncIntervalMs = syncIntervalMs;
    }

    public long getSyncRetryDelayMs() {
        return syncRetryDelayMs;
    }

    public void setSyncRetryDelayMs(long syncRetryDelayMs) {
        this.syncRetryDelayMs = syncRetryDelayMs;
    }
}
