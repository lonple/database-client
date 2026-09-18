package com.lyj.dbc.usercenter.svcsign;

import org.junit.jupiter.api.Test;

import java.security.KeyPair;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 待签串与 ECDSA 签名基本正确性。
 */
class SignCanonicalTest {

    @Test
    void buildAndSignVerify() {
        byte[] body = "{\"a\":1}".getBytes();
        String stringToSign = SignCanonical.build(
                "POST", "/inner/ping", "b=2&a=1", "1710000000", "nonce1", body);
        // query 应字典序
        assertTrue(stringToSign.contains("\na=1&b=2\n"));

        KeyPair pair = EcdsaSignSupport.generateKeyPair();
        String sig = EcdsaSignSupport.sign(pair.getPrivate(), stringToSign);
        assertTrue(EcdsaSignSupport.verify(pair.getPublic(), stringToSign, sig));

        String hash = SignCanonical.sha256Hex(body);
        assertEquals(64, hash.length());
    }
}
