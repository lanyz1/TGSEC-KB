# 卡密授权 so 协议还原（atom 类平台）

## 导出名就是协议说明书

带卡密授权的 so 会把整条协议直接导出，一眼就能拼出流程：

| 导出函数 | 语义 |
|----------|------|
| `atomBypassInitCardKey` | 初始化卡密上下文（写入卡号/设备码） |
| `atomBypassLogin` | 提交卡密登录校验 |
| `atomBypassCheckLogin` | 本地会话是否已登录 |
| `atomBypassQueryStatus` | 查询到期时间/剩余时间 |
| `atomBypassBeginKeyExchange` / `CompleteKeyExchange` | 握手密钥交换（两阶段，通常 ECDH/RSA） |
| `atomBypassShutdown` | 释放 |

拿到导出表就能推：`InitCardKey → Login → QueryStatus` 是主干，`Begin/CompleteKeyExchange`
说明**服务端会下发会话密钥**（意味着单纯算卡密格式没用，要打返回值或服务器）。

## 还原步骤（授权样本内）

```text
① 枚举导出 → 三歩协议成型（无需反汇编）
② Frida hook 每个导出打印参数/返回值，拿到：卡密格式、到期字段名、状态码含义
③ 抓包定位校验域名（hosts + 本地假服务器思路同 net-license-crack）
④ 定倒打点：Login 返回值 / QueryStatus 到期时间 / CheckLogin 布尔
```

## 绕过优先级（从简到重）

| # | 手法 | 说明 |
|---|------|------|
| 1 | 改返回值 | `Interceptor.attach(QueryStatus).onLeave → retval.replace(ptr(0x7fffffff))`（剩余秒数拉满）；不改文件 |
| 2 | 改 CheckLogin | 返回 1 直接放行；对应静态 patch 就是 `mov w0,#1; ret` |
| 3 | 断分支 | 找 Login 失败分支 `CBZ/CBNZ` 对调 或 NOP；OLLVM 下先从字符串找判断点 |
| 4 | 假卡密服务器 | hosts 域到 127.0.0.1 + Flask 回 `{"code":0,"expire":4070908800}`；但 Begin/Complete 握手下要真做密钥交换 |
| 5 | 算法级 keygen | 只有在拿到真卡密样本且算法纯本地时（同 net-license-crack 的 L2 口径） |

别急着反汇编：**导出表 + hook 日志**就能定完协议，这是这族样本性价比最高的路径。

## 内嵌的手工 ELF 解析 = linker 绕过/符号劫持

so 里出现 `e_phoff` 校验、`symbol not found` 这类自实现 ELF 解析代码时，它在干两件事：

1. **自省模块**：不靠 `/proc/self/maps`（易被检测）而是走 `dl_iterate_phdr`/自读 ELF 头找基址；
2. **对抗 so 检测**：把自身模块从链表/映射视图里藏起来，或劫持符号让检测函数返回“干净”。

**检测点（防守侧）**：`/proc/self/maps` 与 linker 模块链表不一致、匿名 rwx 段、
`.bss` 可执行、`dl_iterate_phdr` 回调里对自身模块名做重命名。

## 兄弟卡交接

- 网络验证/卡密平台（天盾/fndata/Nuitka）→ `net-license-crack`（本卡只管 so 形态）
- 客户端状态旗标（isPaid/vip 只在本地）→ `client-state-skip`
- 发卡站/卡密商城服务端 → `faka-card-shop-pentest`、`acg-faka`
