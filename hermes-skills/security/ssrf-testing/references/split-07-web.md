## 六、内网Web攻击利用

### 6.1 内网常见脆弱服务
| 服务 | 端口 | 利用 |
|------|------|------|
| Redis | 6379 | 未授权→RCE（Gopher/Dict）|
| Memcached | 11211 | 未授权访问 |
| Elasticsearch | 9200/9300 | 未授权数据泄露/RCE（CVE）|
| MongoDB | 27017 | 未授权数据访问 |
| MySQL | 3306 | 弱口令/日志写Shell |
| MSSQL | 1433 | 弱口令/xp_cmdshell |
| PostgreSQL | 5432 | 弱口令/CVE |
| FastCGI/PHP-FPM | 9000 | 任意代码执行（Gopher）|
| Tomcat | 8080 | 弱口令管理后台→WAR部署 |
| JBoss | 8080 | JMXInvoker未授权RCE |
| WebLogic | 7001 | 多RCE CVE |
| Jenkins | 8080 | Groovy脚本控制台未授权RCE |
| Docker API | 2375 | 容器创建→逃逸 |
| ZooKeeper | 2181 | 未授权信息泄露 |
| ActiveMQ | 61616 | 反序列化RCE |
| RabbitMQ | 15672/5672 | 管理后台弱口令 |
| etcd | 2379 | 未授权K/V访问 |
| Consul | 8500 | API RCE |
| Nacos | 8848 | 弱口令→配置泄露 |
| Apache Solr | 8983 | RCE CVE |
| CouchDB | 5984 | 未授权访问 |
| Hadoop | 50070 | 未授权RCE |
| Dubbo | 20880 | 反序列化RCE |
| Shiro | 80/443 | RememberMe反序列化 |
| Spring Boot Actuator | 80/8080 | Actuator端点→RCE |
| Struts2 | 80/443 | OGNL注入RCE |

### 6.2 内网Web未授权利用
```
# Tomcat Manager
http://127.0.0.1:8080/manager/html
# 默认凭证tomcat/tomcat、admin/admin
# 可部署WAR包拿Shell

# WebLogic Console
http://127.0.0.1:7001/console/
http://127.0.0.1:7001/uddiexplorer/    （SSRF CVE-2014-4210）
# 默认凭证weblogic/Oracle@123

# JBoss
http://127.0.0.1:8080/jmx-console/
http://127.0.0.1:8080/web-console/
http://127.0.0.1:8080/invoker/JMXInvokerServlet    （反序列化RCE）

# Jenkins
http://127.0.0.1:8080/script
# Groovy脚本执行RCE

# Spring Boot Actuator
http://127.0.0.1:8080/actuator
http://127.0.0.1:8080/actuator/env
http://127.0.0.1:8080/actuator/jolokia     （JNDI注入RCE）
http://127.0.0.1:8080/actuator/heapdump    （堆内存dump泄露密钥）
http://127.0.0.1:8080/env
http://127.0.0.1:8080/eureka/apps

# Apache Solr
http://127.0.0.1:8983/solr/
# RCE via Velocity模板

# Nacos
http://127.0.0.1:8848/nacos/v1/auth/login
# 默认凭证nacos/nacos
http://127.0.0.1:8848/nacos/v1/cs/configs  （配置信息含AK/SK）
```

