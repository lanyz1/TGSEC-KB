# WebShell 全解析（类型 / 检测 / 授权利用 / 清理）

> 双重用途：授权测试中的 RCE PoC 落地，与防守侧检测处置（蓝队视角）。**红线**：只在不属于生产/仅限授权环境的无害证明；禁止非授权系统植入持久后门。本文件重点是「懂它才能防它、才敢用它做最小验证」。

## 一、WebShell 类型全景

### 按语言
| 语言 | 典型形式 | 特征 |
|------|---------|------|
| PHP | `<?php @eval($_POST['x']);?>` | 最常见；`eval`/`assert`/`preg_replace /e`/`create_function` |
| JSP | `<% Runtime.getRuntime().exec(...) %>` | Web 容器内 Java 代码执行 |
| ASPX | `<% Page Language="C#" %>` + 反射加载 | .NET 管道 |
| ASP | `<% Execute("...") %>` | 老古董，IIS |
| Python | Flask/Django 路由 + `exec` | 少但存在，常以「接口」形式 |
| Node | `eval(require('child_process')...)` | 少见，多为 RCE PoC 形态 |

### 按功能/隐蔽度
1. **一句话木马**：最小体积（`eval` + 一个参数），专为流量过 WAF 设计
2. **大马（多功能）**：文件管理+数据库+端口扫描+反弹 shell（蚁剑/冰蝎/哥斯拉的 loader 端）
3. **内存马（无文件）**：注入到运行中进程/JVM，无磁盘文件（Java 中间件 Filter/Servlet/Listener 型）
4. **图片马**：文件头伪装（GIF89a + 代码），靠解析差异触发
5. **加密马**：密文存储 + 解密执行，静态查杀难命中（哥斯拉/冰蝎载荷）

## 二、防守侧检测（蓝队视角）

### 静态特征
- **关键字**：`eval`、`assert`、`base64_decode`、`gzinflate`、`str_rot13`、`create_function`、`preg_replace` + `/e`
- **高危函数组合**：`$_POST`+`eval`、`$_REQUEST`+`system`、`move_uploaded_file`+可写目录
- **混淆模式**：超长字符串拼接、`chr()` 逐字节、变量名全部单字符、`@` 压制错误
- **文件特征**：新近上传的 .php/.jsp/.aspx、非业务目录、权限异常 777/666

### 动态行为
- 进程执行了 `whoami`/`id`/`net user`/`ipconfig`/`wget` 等探查命令
- 访问了系统配置文件（`/etc/passwd`、`web.xml`、`mvc_controller`）
- 异常子进程：Web 容器（php-fpm/java/tomcat）派生 shell 进程

### 流量特征（关键，用于 EDR/IDS）
| 工具 | 特征 |
|------|------|
| 蚁剑 | 流量 base64(URL)+`@ini_set` 前缀；请求头 `User-Agent` 默认值；分块传输 |
| 冰蝎 | AES 加密流量，请求头固定 `Content-Type` 与随机 key 交换（协商阶段可辨） |
| 哥斯拉 | 自定义加密（AES/异或），载荷 base64 后 URL 编码，特征头 `Pragma`/特定 Cookie |

## 三、授权利用（PoC 最小化协议）

拿到 RCE 后只做四步，禁止多走一步：

1. **无害证明**：`id` / `whoami` / `uname -a`（只读，无副作用）
2. **唯一标记证明**：写入唯一标记文件，如 `echo "hunter-$(date +%s)-$RANDOM" > /tmp/hunter_marker.txt`，内容唯一可关联本次测试
3. **出网证明（如需）**：向自己可控的 DNSLOG/VPS 发一次请求，证明出网能力（不做内网横移）
4. **清理**：删除标记文件、删除上传的 PoC 文件、恢复被改动的文件内容

**禁止**：持久后门、反弹 shell 常驻、下载挖矿/勒索工具、读取无关业务数据、内网横向渗透（除非单独授权范围明确包含）。

### 上传点 → WebShell 最短链
```
上传点 → 校验分析（后缀/Content-Type/Magic/解析差异）
   ├─ 直接可执行（少见，说明过滤形同虚设）
   ├─ 绕过：.php5/.phtml/.pht 双写、%00 截断（老）、大小写、夹心（x.php.jpg 需解析器差异）
   ├─ 图片马 + 包含漏洞（LFI + 文件头绕过）
   ├─ 对象存储/云函数（落地不在 Web 根，改打 SSRF/云配置）
   └─ 反序列化（文件落地 + gadget 触发）
→ 命中后立刻进入 PoC 最小化协议 → 报告
```

## 四、提权与横向（ATT&CK 视角）

在授权范围内（如红队演练）评估提权链：
- 容器内：环境变量里的云凭证、挂载的 k8s token、`docker.sock`
- 经典提权：SUID、cron、可写 PATH、sudo 配置、内核 CVE（要评估稳定性与授权范围）
- 横向：凭据复用、内网服务未授权（Redis/ES/Jenkins/MinIO/Nacos）、域内横向（此为独立授权科目）

> 每条动作都要对照授权范围；范围外一律不打、不碰、不驻留。

## 五、报告中的 WebShell 部分

- 报告中明确写出：入口漏洞（上传/命令注入/反序列化）→ 利用链 → 影响（RCE 级别）
- PoC 复现步骤必须可复核（截图 + 完整请求包 + 命令输出）
- 修复建议：输入校验（后缀白名单+内容嗅探）、上传目录禁执行、WAF 规则（关键字+流量特征）、文件完整性监控、容器最小化