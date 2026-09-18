package com.lyj.dbc.usercenter.secrets;

import com.lyj.dbc.usercenter.common.BizException;
import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * 使用 KEK 对库内敏感字段（如 ECDSA 私钥 PEM）做 AES-GCM 加解密。
 */
@Component
public class KekCryptoService {

    private static final String TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int GCM_TAG_BITS = 128;
    private static final int IV_LEN = 12;

    private final SecretKey kek;
    private final SecureRandom secureRandom = new SecureRandom();

    public KekCryptoService(SecretFileStore secretFileStore) {
        String kekMaterial = secretFileStore.readOrCreate(SecretFileStore.FILE_KEK, 32);
        this.kek = deriveAesKey(kekMaterial);
    }

    /** 加密明文，返回 Base64(iv + ciphertext) */
    public String encrypt(String plain) {
        try {
            byte[] iv = new byte[IV_LEN];
            secureRandom.nextBytes(iv);
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, kek, new GCMParameterSpec(GCM_TAG_BITS, iv));
            byte[] cipherBytes = cipher.doFinal(plain.getBytes(StandardCharsets.UTF_8));
            ByteBuffer buffer = ByteBuffer.allocate(iv.length + cipherBytes.length);
            buffer.put(iv);
            buffer.put(cipherBytes);
            return Base64.getEncoder().encodeToString(buffer.array());
        } catch (Exception e) {
            throw BizException.badRequest("KEK 加密失败");
        }
    }

    /** 解密 Base64(iv + ciphertext) */
    public String decrypt(String cipherText) {
        try {
            byte[] all = Base64.getDecoder().decode(cipherText);
            byte[] iv = new byte[IV_LEN];
            byte[] body = new byte[all.length - IV_LEN];
            System.arraycopy(all, 0, iv, 0, IV_LEN);
            System.arraycopy(all, IV_LEN, body, 0, body.length);
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, kek, new GCMParameterSpec(GCM_TAG_BITS, iv));
            return new String(cipher.doFinal(body), StandardCharsets.UTF_8);
        } catch (Exception e) {
            throw BizException.badRequest("KEK 解密失败");
        }
    }

    private static SecretKey deriveAesKey(String material) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] key = digest.digest(material.getBytes(StandardCharsets.UTF_8));
            return new SecretKeySpec(key, "AES");
        } catch (Exception e) {
            throw new IllegalStateException("派生 KEK 失败", e);
        }
    }
}
