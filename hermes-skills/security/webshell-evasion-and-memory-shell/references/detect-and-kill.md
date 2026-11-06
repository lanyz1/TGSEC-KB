# 检测与查杀（文件马 + 内存马）

三条检测线同时上，任一条单独出结论都会漏：**文件静态 → 流量行为 → 内存驻留**。

## 1. 文件静态

| 手段 | 说明 |
|------|------|
| D盾 / 河马 / 长亭 | 常用三联，注意"已知后门变种"与"无后门"的区别 |
| 云查杀（阿里/百度/VT） | 静态 + 行为；上云即泄露样本，授权演练内使用 |
| YARA | webshell 规则集跑全站，适合批量与留存证据 |
| 自写扫描 | `scripts/webshell_static_scan.py`（线索分 + 命中行） |

看什么：敏感函数与动态调用同现、超长高熵单行、字符集异常（PHPFuck 类）、
工具特征片段（哥斯拉 `substr(md5(`、冰蝎 `openssl_decrypt`+`$_POST`）、
最近修改时间与上传目录、`.user.ini`/`.htaccess` 劫持。

## 2. 流量行为

```text
哥斯拉：Cookie 值末尾分号；首包偏大；响应 16+32+16（md5 前后包裹 base64）
冰蝎：密钥 = 连接密码 MD5 前 16 位；Accept/Content-Type 固定；响应 {"status":"success","msg":...}
蚁剑：UA 含 antSword；POST 单参数；PHP 配置语句
通用：POST 到不存在的页面却返回 200；body 全密文且参数名固定；请求体高熵；
      同一 URL 被固定周期访问（心跳）；UA 与该站受众不匹配
```

## 3. 内存（无文件马只能靠这层）

```bash
# 在线诊断（arthas）
sc -d *Filter*            # 看 filter 类是否陌生/重名可疑
sm -d <可疑类>            # 方法签名：是否带 command/exec 参数
classloader -l            # 有无异常类加载器
# 快速清点
jcmd <pid> GC.class_histogram | head -50
jmap -histo:live <pid> | head -50
```

排查位置（Java 容器）：

| 位置 | 可疑点 |
|------|--------|
| `StandardContext.filterConfigs` | 追加的 Filter（内存马最常见落点） |
| `StandardContext.servletMappings` | 新增 URI→Servlet 映射 |
| `applicationEventListeners` | 追加的 Listener |
| `pipeline.valves` | 追加的 Valve |
| `adaptedInterceptors` | 追加的 Spring 拦截器 |
| 启动参数 / 已加载 agent | `-javaagent`、临时目录里的 jar（Agent 型） |

判据：**重启后仍在 = 有文件或 Agent**（一定去磁盘找）；重启即失效 = 纯内存马（查注册点与来源入口）。

## 处置流程

```text
① 隔离与固定：样本哈希、进程与端口快照、内存/堆 dump、日志存档（先取证再清理）
② 定入口：结合 access log 找到写入/注入请求（配合 attacker-tracing-and-counterstrike 画像）
③ 清理：停服务 → 删文件/重启释放内存马 → 改所有相关凭据 → 补入口补丁
④ 复检：重扫文件 + 重查内存 + 流量回放确认特征消失
⑤ 监控：对注册点与关键路径上监控；记录时间线入报告
```

**别只删文件**：内存马重启前一直在；**别只重启**：文件马还在盘上。
