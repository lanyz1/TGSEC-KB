## 八、溯源追踪与威胁情报

### 8.1 IOC提取与共享
```
IOC类型：
- Hash（MD5/SHA256/SSDeep/TLSH）
- IP/Domain/URL/注册域名（whois/证书指纹JA3/JA3S）
- 文件名/路径/互斥量名称
- 注册表键值/计划任务名
- C2协议特征（User-Agent、Beacon间隔、公钥）
- YARA规则/Sigma规则

共享格式：STIX 2.1 / TAXII 2、OpenIOC、MISP 事件
共享渠道：MISP、企业威胁情报平台、行业CERT、国家CERT
```

### 8.2 攻击者画像
```
分析维度：
- 攻击时间规律（工作时区推断：UTC+8/UTC+3/UTC-5）
- 使用语言（代码注释/文件名/字符串：中文/俄语/英语/阿拉伯语）
- 工具特征（C2框架：Cobalt Strike/Metasploit/Sliver/自定义）
- TTPs映射（MITRE ATT&CK 分组匹配：APT28/Lazarus/BlackCat等）
- 目标选择（行业/地域偏好、社会工程话术）
- 基础设施（历史域名注册模式、托管商偏好、基础设施复用）
```

### 8.3 溯源反查方法
```
1. C2基础设施：域名whois反查注册人邮箱（注意隐私保护）、历史解析记录（Passive DNS）
2. 证书指纹：JA3/JA3S 匹配公开威胁情报库（如 ja3er）
3. 基础设施共享：IP段/ASN 聚类、域名关联图
4. 样本聚类：SSDeep 相似度、代码同源性（复用样本比较）
5. 攻击归因注意事项：归因需高置信度，避免误报；公开报告由专业团队（Mandiant/奇安信等）主导
```

