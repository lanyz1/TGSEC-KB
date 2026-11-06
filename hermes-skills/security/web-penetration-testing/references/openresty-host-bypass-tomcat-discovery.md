# OpenResty 402→302 Host Header 绕过 & Apache Tomcat 8.0.36 发现

## 场景

源站 IP 已通过 crt.sh 历史 SSL 证书 SAN 分析找到（如 x3891.vip → 20.6.183.83），但所有路径返回 **402 Payment Required**（OpenResty Content Gate）。

## 诊断：402 → 302 Host Header 绕过

将 Host header 设为源站 IP 本身，可触发 **302 Found** 而非 402：

```bash
# 带域名 Host → 402 (CDN校验)
curl -skI -H "Host: x3891.vip" "https://20.6.183.83:5067/"
# → 402 Payment Required

# 带IP Host → 302 (绕过CDN校验)
curl -skI -H "Host: 20.6.183.83" "https://20.6.183.83:5067/"
# → 302 Found → http://20.6.183.83/
```

**原理**：OpenResty 配置中有 Host header 校验——CDN 转发时带正确 Host，直连时 Host 为 IP 则返回重定向。302 目标可揭示后端端口架构（如重定向到 HTTP 而非 HTTPS）。

## OpenResty 内部端口路由

不同 Host header 映射到不同后端服务端口：

```bash
# 映射表（x3891.vip 实例）
Host: x3891.vip       → :5067  (主站)
Host: www.x3891.vip   → :7822  (www端)
Host: m.x3891.vip     → :7822  (移动端)
```

## Apache Tomcat 8.0.36 发现

### 通过 415 错误泄露

当 OpenResty 代理的某一路由返回 415 Unsupported Media Type + Apache Tomcat 签名时：

```bash
curl -sk -X POST "https://target:9016/gameChart/getCPCPChart" -H "Content-Type: application/json" -d ''
# → HTTP 415 + Apache Tomcat/8.0.36 + Tomcat 错误页面
```

### AJP13 端口确认

对源站 IP 做端口扫描确认 Tomcat AJP 连接器：

```bash
nmap -sT -Pn -p 8009 <origin-ip>
# → 8009/tcp open  ajp13
```

### 已知漏洞

| CVE | 类型 | 利用方式 |
|:----|:-----|:---------|
| CVE-2020-1938 | Ghostcat (AJP文件读取) | 通过 AJP13 协议读取 WEB-INF/web.xml 等任意文件 |
| CVE-2017-12617 | PUT 上传 RCE | PUT /path/test.jsp 上传 webshell（需 enabled=true） |
| CVE-2017-12615 | PUT 上传 (PUT 方法) | 类似 CVE-2017-12617 |

### 绕过 OpenResty 攻击 Tomcat

402 屏障在前，Tomcat 在 OpenResty 之后。攻击路径：

1. **从境外 VPS 直连源站 IP** — 绕过 GFW 对 CDN 的限速
2. **尝试 AJP 直连端口 8009** — 用 Ghostcat payload 读取文件
3. **寻找未受 OpenResty 保护的路径** — nmap 全端口扫描 + HTTP 探测
4. **Tomcat Manager 爆破** — 如果 manager 路径暴露且不受 402 保护

## 参考

- 实战案例: x3891.vip (新葡京娱乐城) → Azure 香港 20.6.183.83
- 源站 IP 发现方法: `cdn-origin-discovery-via-old-certs.md`
