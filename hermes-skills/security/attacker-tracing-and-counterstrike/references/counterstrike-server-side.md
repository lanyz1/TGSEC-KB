# 反制 playbook（服务端 / 基础设施侧）

## 1. rogue MySQL —— 读攻击者客户端任意文件

```text
原理：LOAD DATA LOCAL 读哪个文件由**服务端返回的 file-transfer 请求**决定，不是客户端。
      伪造 MySQL 服务端在认证成功后随时可发 file-transfer 请求，客户端即把该文件回传
      （MySQL 官方文档原话："A patched server could in fact reply with a file-transfer request
      to any statement"）。
前置：客户端连接带 CLIENT_LOCAL_FILES（PHP <7.2 默认开；Python/Java 驱动需 local_infile/--enable-local-infile）。
场景：蜜罐挂一个"弱口令 MySQL"（端口 3306/3307，账号 root 空口令/readme），
      攻击者（或其扫描脚本、数据迁移工具）一连 → 直接读走它的
      ~/.ssh/id_rsa、~/.zsh_history、扫描器配置、浏览器 Cookie 库、/etc/passwd。
实现：Rogue-MySql-Server 一类假服务端，改读文件清单后监听即可。
判据：文件内容落地到你自己机器；内容哈希存档。
```

同类思路：假 FTP / 假 HTTP 更新服务 / 假 Redis（记录攻击者写入的 key、命令、来源 IP）、
假 Kubernetes API（记录 kubeconfig 携带的令牌）、假 OVDP/VPN 门户（记录凭据）。

## 2. sqlmap 反制

```text
(a) 构造注入页 + 命令管道符回注
    把目标页做成"注入点"，参数值固定；当攻击者用 sqlmap 的命令执行类特性时，
    服务端返回内容中带管道符命令（如 ping "`ls`" / nslookup 反引号包裹），
    由 sqlmap 在**本地**拼接执行 → 攻击者机器回连你的监听域名。
    前置：sqlmap 的 os 执行链路 + 你的域名解析。
    判据：攻击者机 DNS/ICMP 回连日志。
(b) 见上 rogue MySQL：sqlmap 连库路径若开了 local_infile 同样可读其本机文件。
(c) 弱面：暴露的 API/日志里泄露的 sqlmap 输出文件（session 文件含命中的库表与目标）可反推其资产。
```

## 3. CS TeamServer 定位与打击

```text
定位：请求 <4 个随机字符路径>（如 /aaa9），404 且响应体为空即命中 checksum8 特征（32 位总和=92 / 64 位=93）。
      再配合默认 profile 的 C2 URI、证书 CN 特征、jQuery 版本确认。
打击：登录面爆破（csbruter 一类；CS 默认口令/admin 类配置极常见）；
      拿下后读 beacon 配置与 metadata → 拿到攻击者全部受害机、监听器、上传下载记录。
纪律：只有在明确授权（防守方/演练授权）下执行；全程留操作日志。
```

## 4. 蜜罐与蜜标（把人钓进记录面）

```text
蜜罐：HFish 一类产品 + 自建高交互服务；重点不是"挡住"，而是**记录**：
      交互命令、上传样本、登录凭据、扫描器 UA、攻击者真实出口。
蜜标（honeytoken）投放物与判据：
  - 带唯一标记的"数据库备份"（内含标记凭据）→ 谁下载/连接即暴露
  - 假 VPN/OVPN 配置：auth-user-pass 指向你的服务 → 记录其用户名/密码与 IP
  - 假 Git 仓库/网盘里的 .env、私钥、SSO 凭据
  - 假内网页面里的 SSO/OAuth 回调 → 取社交身份（配合下条）
前端画像：蜜罐页面植入 JSONP/XSS/指纹脚本；攻击者用浏览器访问时
      可尝试获取其内网身份、社交账号、浏览器指纹（老标签扫描技术，成功率取决于浏览器版本）。
判据：画像数据（账号/邮箱/IMEI 类标识）与回连日志。
```

## 5. 拿到攻击者机器之后

```text
① 固定证据：内存/磁盘镜像 + 哈希（host-ir-check）
② 提取身份：SSH known_hosts、shell history、浏览器记录、C2 配置、支付/注册信息
③ 横向：同 C 段/同组织其他跳板（只做授权范围内）
④ 上报与清理：按演练规则；改动前先备份可回滚
```

**失败也记录**：版本已修、无回连、蜜标无人取——写进报告，别美化。
