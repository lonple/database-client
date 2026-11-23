package com.lyj.dbc.knowledge.nacos;

import com.alibaba.nacos.api.PropertyKeyConst;
import com.alibaba.nacos.api.naming.NamingFactory;
import com.alibaba.nacos.api.naming.NamingService;
import com.lyj.dbc.knowledge.config.NacosProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.DisposableBean;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.Enumeration;
import java.util.Properties;

@Component
public class NacosRegistrar implements ApplicationRunner, DisposableBean {
    private static final Logger log = LoggerFactory.getLogger(NacosRegistrar.class);

    private final NacosProperties properties;
    private final Environment environment;
    private NamingService naming;
    private String serviceName;
    private String ip;
    private int port;

    public NacosRegistrar(NacosProperties properties, Environment environment) {
        this.properties = properties;
        this.environment = environment;
    }

    @Override
    public void run(ApplicationArguments args) {
        serviceName = environment.getProperty("spring.application.name", "dbc-knowledge");
        port = environment.getProperty("server.port", Integer.class, 8010);
        ip = advertiseHost();
        try {
            Properties props = new Properties();
            props.setProperty(PropertyKeyConst.SERVER_ADDR, properties.getServerAddr());
            naming = NamingFactory.createNamingService(props);
            naming.registerInstance(serviceName, ip, port);
            log.info("Nacos registered {} {}:{}", serviceName, ip, port);
        } catch (Exception e) {
            log.warn("Nacos register skipped: {}", e.getMessage());
        }
    }

    @Override
    public void destroy() {
        if (naming == null) {
            return;
        }
        try {
            naming.deregisterInstance(serviceName, ip, port);
        } catch (Exception e) {
            log.warn("Nacos deregister failed: {}", e.getMessage());
        }
    }

    private String advertiseHost() {
        if (properties.getAdvertiseHost() != null && !properties.getAdvertiseHost().isBlank()) {
            return properties.getAdvertiseHost().trim();
        }
        try {
            Enumeration<NetworkInterface> nics = NetworkInterface.getNetworkInterfaces();
            while (nics.hasMoreElements()) {
                NetworkInterface nic = nics.nextElement();
                if (!nic.isUp() || nic.isLoopback()) {
                    continue;
                }
                Enumeration<InetAddress> addrs = nic.getInetAddresses();
                while (addrs.hasMoreElements()) {
                    InetAddress addr = addrs.nextElement();
                    if (addr instanceof Inet4Address && !addr.isLoopbackAddress()) {
                        return addr.getHostAddress();
                    }
                }
            }
        } catch (Exception ignored) {
            // fall through
        }
        return "127.0.0.1";
    }
}
