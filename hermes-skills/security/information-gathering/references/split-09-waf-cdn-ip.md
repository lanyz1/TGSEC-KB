## 八、WAF/CDN 识别与真实 IP 溯源

### 8.1 WAF 识别
```bash
wafw00f https://target.com

# 手动验证：发送无害探测包观察拦截特征
curl -X POST https://target.com/ -d "id=1' AND '1'='1"
# 观察：拦截页特征 / 响应头变化 / 状态码突变 / 内容差异

# 常见 WAF 特征
# Cloudflare: server: cloudflare + cf-ray 头
# 阿里云WAF / 腾讯云WAF / 安全狗 / D盾 / 云锁 / 长亭雷池(SafeLine) / 创宇盾
# 识别到 WAF → 调整扫描策略（见 6.3）→ 后续利用需 WAF 绕过（参考各漏洞利用技能）
```

### 8.2 CDN 识别
```bash
# CNAME 检查
dig cname www.target.com
# *.cloudfront.net / *.cdn.cloudflare.net / *.kunlun*.com(阿里CDN) / 腾讯云CDN / 网宿

# 多节点对比：同一域名解析结果是否多地不同（是→CDN）
# 工具：17CE 超级Ping / IPIP.net / 站长工具
# 老牌：CloudFail / CloudUnflare（已部分失效，配合历史DNS使用）
```

### 8.3 真实 IP 溯源全手段（红队核心技能）
```
1. 历史 DNS：SecurityTrails/DNSDB/微步，CDN 上线前的 A 记录（最高效）
2. 子域名排查：未接入 CDN 的子域（mail/oa/ftp/vpn/测试域）直连源站
3. 邮件头：发送邮件到目标，查 Received: 字段中的源 IP
4. 证书关联：Censys/crt.sh 按证书指纹反查所有托管该证书的 IP（含源站）
5. 空间引擎：FOFA "cert=目标域" 按证书找 IP；Shodan ssl.cert.subject.cn
6. 错误页/功能点：SSRF、文件包含、网站地图、报错日志泄露内网 IP
7. 特定技术特征：F5 LTM Cookie / Citrix NSC / 部分负载均衡头可解码真实 IP
8. 云存储回源：对象存储的 CNAME 常暴露存储桶区域与真实存储节点
9. 移动端直连：App/小程序常直接请求源站 IP（见第十章）
10. 验证：用候选 IP 直接 HTTP 访问，对比页面内容/证书/Server 头是否与域名一致
```

