---
name: admin-file-service-rw-primitive
description: Use when 后台文件服务 basePath 可控：任意读写原语与天花板判定。
version: 1.0.0
license: MIT
platforms: [windows]
---

# 后台文件服务 → 任意目录读/写原语（及其天花板）

> 适用：admin/管理后台自带「存储配置 + 上传 + 下载」三件套，且**存储根（basePath/rootDir）
> 可由 API 写**。典型：芋道 ruoyi-vue-pro `/infra/file-config` + `LocalFileClient`。
> 前置：拿到任意后台身份（含 mock/测试票、越权到的低权票），能调该模块接口。
> 用户提到 file-config、basePath、LocalFileClient、file/upload、file/{id}/get、
> 任意文件读、pod 主机名、SA token 时使用。
> 勿与「上传只落 OSS/CDN、路径不可控」的上传卡、或仅 heapdump 的 Actuator 卡混用。

---

## 0. ★ 第一原则：`code:0` 不等于生效

这条原语上最容易亏时间的地方，是**接口回成功但什么也没发生**。
已知三种「伪成功」，全都表现为正常返回：

| 伪成功 | 机制 | 识别 |
|---|---|---|
| 配置写入被静默拒 | 缺**必填字段**（芋道 `domain`），接口照回成功，`basePath` 未变 | 补齐字段后用 `page`/`get` **读回**对比 |
| 写入矩阵「全成功、文件名全同」 | 配置**按 configId 客户端缓存**，改的不是实际生效的实例 | 每次**新建**一个配置对象、用新 id 读写 |
| 定时任务「建成功但不执行」 | 框架语义不同（handler 必须是实现接口的 Spring bean） | 用**读原语回读落地物**，或看业务层报错 |

⇒ 纪律：**任何写操作都用第二条独立通道读回**。最干净的通道就是本卡自己的「读文件」原语
——它**不依赖出站网络**，比 OOB / webhook / 外部回连都可靠。

---

## 1. 落地四步

```text
① 建/改「存储配置」：storage=本地、basePath=目标目录、其余必填字段补齐
② 读回配置（page/get）确认 basePath 真的变成目标目录 ← 不做这步后面全是白跑
③ 读：GET <模块>/file/{id}/get/{单段文件名}
   写：POST <模块>/file/upload（multipart）落到该 basePath
④ 收尾：basePath 改回原值 / 删自建配置，自己的文件一并记名回滚
```

- **每个配置对象独立缓存自己的 basePath**：要换目录就**新建一个**并记住 id，
  不要指望 `update` 老 id 立刻生效。这是「任意目录读写」的真正开关。
- 存储类型字段（芋道 `storage`）必须选**本地**档；S3/OSS/FTP 档写的是远端，不是本机文件系统。
- 落到目录里之后**内容与扩展名可控**，这决定它能不能当 webshell / 计划任务载体。

---

## 2. 读原语语义（先摸 oracle，再谈利用）

| 情况 | 返回 | 解读 |
|---|---|---|
| 文件存在 | `200` + 原文 | 可读 |
| 不存在 / 无权限 | 网关 `200` + 业务 `{"code":500,"message":"系统异常"}` | **≠ 漏洞不存在**，只是这个路径没有 |
| `File.length()==0` 的文件 | 空 body | **procfs 永远读不到**：`/proc/self/environ`、`/proc/self/cmdline` |
| 名字带斜杠（多段） | `404` | 形态约束：**basePath 指目录 + 单段文件名** |

没有目录列表接口 ⇒ 把「换单段名 + 看 200/500」当**目录枚举器**用：
`/etc/{passwd,shadow,hostname,resolv.conf}`、`/root/.bash_history`、`/var/run/secrets/...`、
`/app/{application.yaml,...}` 逐个试。

---

## 3. 写原语的天花板（决定别再往哪投时间）

本地实现常把文件名固定为 **`<md5(内容)>.<扩展名>`** ⇒ **扩展名可控、文件名不可控**。
下列落点**全部无效**，别反复试：`~/.ssh/authorized_keys`、`application.yaml`、
`/etc/cron.d/<name>`、`/etc/profile.d/*.sh`、`ld.so.preload`、webroot 下的 webshell。

剩下的方向只有：**目标会「扫目录 + 按扩展名执行/服务」**的场景，以及
**把内容写进自己的位置再用读原语取回**（零外带回读/外带信道）。
确认名字不可控就**果断换面**，不要在这一跳上磨。

---

## 4. 读原语最值钱的用法：判环境、定闭环节点

拿到任意读后**前 10 分钟先读环境**，再决定值不值得继续：

| 读 | 得到 | 含义 |
|---|---|---|
| `/etc/hostname` | `app-<rs>-<pod>` 形态 | 跑在 **K8s Pod**，不是裸机 |
| `/etc/shadow` 可读 | `root:!::0:::::` | 应用**以 root 跑**，读侧就是 root |
| `/etc/resolv.conf` | `nameserver 192.168.x.x` + `search <ns>.svc.cluster.local` | 集群 **Service CIDR** ⇒ K8s API = **CIDR 首个 IP:6443** |
| `/var/run/secrets/kubernetes.io/serviceaccount/{token,namespace,ca.crt}` | SA token | 是否值钱取决于下一条 |

**★ 闭环节点判定**：SA token 只有在**能在 Pod 内发 HTTP** 时才值钱。
API Server 无公网暴露（6443/8443/10250 关闭）时，token 单独到手 = **零收益**，
它只说明「**下一步必须先拿到 Pod 内代码执行**」，不是「集群接管在望」。
别在拿到 token 后继续找 API 出口（死路），回到「Pod 内执行」这一跳。
把「内网地址是否可达」当场判掉，再谈 RDS/Redis/内部调度器那条链。

---

## 5. 面判读：`403` 与 `404` 别混（会误判整片攻击面）

| 现象 | 含义 | 动作 |
|---|---|---|
| `404 {"status":404,"path":"..."}` | **该模块未注册**（部署没带这个功能） | 这条路**不存在**，补权限也打不开，换面 |
| `403「没有该操作权限」` | 路由在，被**菜单/角色权限门**挡住 | 可补菜单权限（可逆、仅本租户）后回来打 |
| `500 系统异常` | 路由在，执行到业务层抛错 | 参数/前置条件问题，靠差分试 |

别把「某模块在别的部署上存在」当成「这台也有」：芋道有「多数据源」模块时可控
JDBC URL ⇒ 恶意 MySQL/PG 反序列化是可行的反射 RCE，但**部分部署根本没注册（全 404）**
⇒ 这条链当场不存在。**先探再规划**。

---

## 6. 收尾与报告口径

- 只读为主；写只落**自己的**文件、自建配置，**记下每个 id 与文件名**，收尾一起删/改回。
- 报告分三档，不许跳级自夸：**原语成立**（读/写通）≠ **拿到执行** ≠ **拿到主机/集群**。
- 「已具备但未启用」的通道（写部署桶、改生产制品、动别人数据）单列，
  **需用户明确同意才动**，不要在自主推进里顺手做掉。

---

## 7. 相关卡

- 芋道具体端点/字段/现成配方：`references/yudao-infra-file-config-recipe.md`
- 定时任务反射 RCE（**RuoYi 系**才成立）：`ruoyi-quartz-whitelist-bypass-el-rce` ——
  ⚠️ 该卡与 `yudao-daifu-mock-file-rce` 均为用户自有卡，本卡只作对照引用，不改写它们。
- 拿到身份后先填读写矩阵：`object-matrix-authz`
