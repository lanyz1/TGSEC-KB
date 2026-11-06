## 3. Fastjson 家族(核心决策)

### 指纹
- `{"@type":"java.lang.Class"...}` 报错/超时差异;`fastjson` 版本号在报错/响应差异
- 区分 Fastjson1 vs 2: `{"@type":"java.lang.AutoCloseable"}` 响应差异

### AutoType 绕过时间线
| 版本 | 绕过 | 手法 |
|---|---|---|
| ≤1.2.24 | 无限制 | 直接 @type + JNDI |
| 1.2.25-41 | L 前缀 | `Lcom.sun.rowset.JdbcRowSetImpl;` |
| 1.2.25-42 | 双写 | `LLcom...;;` |
| 1.2.25-43 | 方括号 | `[com.sun...` |
| 1.2.25-47 | 缓存通杀 | java.lang.Class 缓存绕过 checkAutoType |
| 1.2.68+ | expectClass | 二次解析绕过(到 1.2.83) |
| **1.2.83** | **Gadget-free RCE** | CVE-2026-16723(镜像 §三.6) |
| **Fastjson2** | **FNV-1a 哈希碰撞** | QVD-2026-45876(镜像 §) |

### 利用链选择(不出网优先)
| 链 | 场景 |
|---|---|
| JNDI | 出网首选(JdbcRowSetImpl) |
| BCEL ClassLoader | 不出网 |
| TemplatesImpl | 不出网(需 parseObject) |
| c3p0 WrapperConnectionPoolDataSource | 不出网 |
| MySQL Connector | 文件读写/RCE |
- **SafeMode**(1.2.68+ 全局开关)= 唯一有效阻断,开启则放弃 AutoType 面

