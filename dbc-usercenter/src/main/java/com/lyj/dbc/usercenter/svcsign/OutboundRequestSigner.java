package com.lyj.dbc.usercenter.svcsign;

import com.lyj.dbc.usercenter.app.vo.AppKeySignResultVO;
import org.springframework.stereotype.Component;

import java.security.SecureRandom;
import java.util.Base64;
import java.util.Map;

/**
 * 出站加签：向用户中心 HTTP 代签后组装请求头。
 */
@Component
public class OutboundRequestSigner {

    public static final String H_CLIENT_ID = "X-Dbc-Client-Id";
    public static final String H_KEY_ID = "X-Dbc-Key-Id";
    public static final String H_TIMESTAMP = "X-Dbc-Timestamp";
    public static final String H_NONCE = "X-Dbc-Nonce";
    public static final String H_SIGNATURE = "X-Dbc-Signature";

    private final CenterSignClient centerSignClient;
    private final SecureRandom secureRandom = new SecureRandom();

    public OutboundRequestSigner(CenterSignClient centerSignClient) {
        this.centerSignClient = centerSignClient;
    }

    public Map<String, String> signHeaders(String method, String path, String query, byte[] body) {
        String ts = String.valueOf(System.currentTimeMillis() / 1000);
        String nonce = randomNonce();
        AppKeySignResultVO signed = centerSignClient.sign(method, path, query, ts, nonce, body);
        return Map.of(
                H_CLIENT_ID, centerSignClient.clientId(),
                H_KEY_ID, signed.getKid(),
                H_TIMESTAMP, signed.getTimestamp(),
                H_NONCE, signed.getNonce(),
                H_SIGNATURE, signed.getSignature()
        );
    }

    private String randomNonce() {
        byte[] buf = new byte[16];
        secureRandom.nextBytes(buf);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(buf);
    }
}
