package com.lyj.dbc.usercenter.svcsign;

import com.lyj.dbc.usercenter.common.BizException;

import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.Signature;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;
import java.security.spec.ECGenParameterSpec;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;

/**
 * ECDSA P-256 签名与验签。
 */
public final class EcdsaSignSupport {

    public static final String ALG = "ES256";

    private EcdsaSignSupport() {
    }

    public static KeyPair generateKeyPair() {
        try {
            KeyPairGenerator gen = KeyPairGenerator.getInstance("EC");
            gen.initialize(new ECGenParameterSpec("secp256r1"));
            return gen.generateKeyPair();
        } catch (Exception e) {
            throw new IllegalStateException("生成 ECDSA 密钥对失败", e);
        }
    }

    public static String toPemPublic(PublicKey key) {
        String b64 = Base64.getMimeEncoder(64, "\n".getBytes(StandardCharsets.US_ASCII))
                .encodeToString(key.getEncoded());
        return "-----BEGIN PUBLIC KEY-----\n" + b64 + "\n-----END PUBLIC KEY-----";
    }

    public static String toPemPrivate(PrivateKey key) {
        String b64 = Base64.getMimeEncoder(64, "\n".getBytes(StandardCharsets.US_ASCII))
                .encodeToString(key.getEncoded());
        return "-----BEGIN PRIVATE KEY-----\n" + b64 + "\n-----END PRIVATE KEY-----";
    }

    public static PublicKey parsePublicPem(String pem) {
        try {
            String normalized = pem
                    .replace("-----BEGIN PUBLIC KEY-----", "")
                    .replace("-----END PUBLIC KEY-----", "")
                    .replaceAll("\\s", "");
            byte[] der = Base64.getDecoder().decode(normalized);
            return KeyFactory.getInstance("EC").generatePublic(new X509EncodedKeySpec(der));
        } catch (Exception e) {
            throw BizException.badRequest("公钥 PEM 无效");
        }
    }

    public static PrivateKey parsePrivatePem(String pem) {
        try {
            String normalized = pem
                    .replace("-----BEGIN PRIVATE KEY-----", "")
                    .replace("-----END PRIVATE KEY-----", "")
                    .replaceAll("\\s", "");
            byte[] der = Base64.getDecoder().decode(normalized);
            return KeyFactory.getInstance("EC").generatePrivate(new PKCS8EncodedKeySpec(der));
        } catch (Exception e) {
            throw BizException.badRequest("私钥 PEM 无效");
        }
    }

    public static String sign(PrivateKey privateKey, String stringToSign) {
        try {
            Signature signature = Signature.getInstance("SHA256withECDSA");
            signature.initSign(privateKey);
            signature.update(stringToSign.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(signature.sign());
        } catch (Exception e) {
            throw new IllegalStateException("ECDSA 签名失败", e);
        }
    }

    public static boolean verify(PublicKey publicKey, String stringToSign, String signatureBase64Url) {
        try {
            Signature signature = Signature.getInstance("SHA256withECDSA");
            signature.initVerify(publicKey);
            signature.update(stringToSign.getBytes(StandardCharsets.UTF_8));
            byte[] sig = Base64.getUrlDecoder().decode(signatureBase64Url);
            return signature.verify(sig);
        } catch (Exception e) {
            return false;
        }
    }

    public static boolean isEc(PrivateKey key) {
        return key instanceof ECPrivateKey;
    }

    public static boolean isEc(PublicKey key) {
        return key instanceof ECPublicKey;
    }

    @SuppressWarnings("unused")
    public static PrivateKey parsePrivatePkcs8(byte[] pkcs8) {
        try {
            return KeyFactory.getInstance("EC").generatePrivate(new PKCS8EncodedKeySpec(pkcs8));
        } catch (Exception e) {
            throw new IllegalStateException("私钥解析失败", e);
        }
    }
}
