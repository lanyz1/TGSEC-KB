## Pitfalls
- 别只扫 /actuator/health 就结案(只证明存在,不利用)
- heapdump 别只 strings 扫字节(可能漏对象图内凭据)→ 用 jar 工具拆对象图
- Shiro 爆破密钥: 判断信号是 deleteMe 有无,不是响应码
- Fastjson: 高版本先试缓存绕过/expectClass,别一上来旧 payload
- 2026 CVE 情报在镜像卡里最全(spring AI/cloud config 批量、shiro 新认证绕过、fastjson2 碰撞),实战前翻镜像

