# Java Gadget 链矩阵与反序列化指纹

> 反序列化利用的核心：认出序列化格式（指纹）→ 锁定库版本（选链）→ ysoserial 生成 → 验证。均为授权测试手法。

## 1. 指纹速查（先认出格式再谈利用）

### Magic Bytes 表
| Magic Bytes (Hex) | Base64 前缀 | 格式 | 语言 |
|---|---|---|---|
| `AC ED 00 05` | `rO0AB` | Java 序列化对象 | Java |
| `00 01 00 00 00 FF FF FF FF` | `AAEAAAD/////` | .NET BinaryFormatter | .NET |
| `FF 01` | `/w` | .NET ObjectStateFormatter (ViewState) | .NET |
| `80 02`–`80 05` | 不定 | Python pickle (协议 2-5) | Python |
| `89 50 4E 47` | `iVBOR` | PNG（可能是 phar polyglot） | PHP |
| `4F 3A` | `Tz`（`O:`） | PHP 序列化对象 `O:N:"Class"` | PHP |
| `61 3A` | `YT`（`a:`） | PHP 序列化数组 | PHP |
| `04 08` | 不定 | Ruby Marshal | Ruby |
| `1F 8B` | `H4s` | Gzip（可能包裹序列化数据） | 任意 |
| `48 02` / `63` | 不定 | Hessian (2.0 / 1.0) | Java |

### Content-Type 高危面
| Content-Type | 风险 |
|---|---|
| `application/x-java-serialized-object` | Critical |
| `application/x-java-serialized-object-xml` | Critical（XMLDecoder） |
| `x-application/hessian` / `application/x-hessian` | Critical |
| `application/x-amf` | High（常包 Java） |
| `application/x-yaml`（带 `!!` tag） | High（YAML.load） |
| `application/json` 带 `$type` | Critical（JSON.NET TypeNameHandling） |
| `application/xml` 带可疑元素 | Critical（XStream/XMLDecoder） |

### 参数名即指纹
| 参数/Cookie | 格式 | 产品 |
|---|---|---|
| `rememberMe` | Java 序列化+AES | Apache Shiro |
| `__VIEWSTATE` | ObjectStateFormatter | ASP.NET WebForms |
| `JSESSIONID` + 二进制 cookie | Java 序列化 | 各类 Java 服务器 |
| `rack.session` | Ruby Marshal | Rails |
| `ci_session` | PHP 序列化 | CodeIgniter |

**快速识别**：`echo "BASE64" | base64 -d | xxd | head -1` 对表。

## 2. CommonsCollections 链版本兼容矩阵

| 链 | 库版本 | JDK 约束 | 执行类型 |
|----|--------|---------|---------|
| CC1 | CC 3.0–3.2.1 | JDK < 8u72（InvokerTransformer 被过滤） | `Runtime.exec()` |
| CC2 | CC 4.0 | 无 | `TemplatesImpl` 字节码 |
| CC3 | CC 3.0–3.2.1 | JDK < 8u72 | `TemplatesImpl` |
| CC4 | CC 4.0 | 无 | `TemplatesImpl` |
| CC5 | CC 3.x | JDK ≥ 8 可用 | `TiedMapEntry` → exec |
| **CC6** | CC 3.1–3.2.1 | 全 JDK | `HashSet` 触发 exec |
| **CC7** | CC 3.1–3.2.1 | 全 JDK | `Hashtable` 触发 |

**推荐优先序：CC6 → CC7 → CC5**（兼容面最广，无 JDK 版本约束）。

## 3. CommonsBeanutils / Spring / JDK-Only

| 链 | 依赖 | 要点 |
|----|------|------|
| CB1 | CommonsBeanutils 1.x | `BeanComparator` + `PriorityQueue`，配合 `TemplatesImpl` |
| CB2-4 | CB + XString 等变体 | 反序列化黑名单绕过常用替代 |
| Spring1/2 | Spring core+beans | `AbstractPointcutAdvisor` 等 gadget |
| JDK-only | 无外部依赖 | `javax.management.BadAttributeValueExpException` + `TemplatesImpl`；黑名单环境首选 |

**选链决策树**：
```
反序列化点确认
├─ 有 ysoserial gadget 白名单（黑名单环境）
│   ├─ 禁 CC → 试 CB / Spring / JDK-only / 自写
│   └─ 禁 TemplatesImpl → 找 exec 型链（CC1/5/6/7 exec 路径）
├─ 无过滤 → CC6 打全场
└─ 非 Java 格式（pickle/marshal/php）→ 另用对应工具
```

## 4. SnakeYAML / Hessian / Kryo / XStream

| 格式 | 利用要点 |
|------|---------|
| SnakeYAML | `!!javax.script.ScriptEngineManager` + URLClassLoader 从恶意 jar 加载 SPI；或 `!!com.sun.rowset.JdbcRowSetImpl` 打 JNDI |
| Hessian | `RemoteClass`/`HashMap` 触发；版本 1.0 vs 2.0 载荷不同 |
| Kryo | `TemplateImpl` 链，需序列化注册类白名单缺失 |
| XStream | `com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl` 经典；watch `application/xml` 带 class 元素 |
| JSON.NET | `$type` 全限定名 → `TypeNameHandling.All` 即打 |

## 5. 验证流程（授权 PoC）

```
1. 指纹：magic bytes / Content-Type / 参数名 三路对表
2. 版本：依赖库版本（前端 bundle / 报错栈 / 版本指纹接口）
3. 选链：按版本矩阵/黑名单决策树
4. 生成：ysoserial <gadget> <command> | base64
5. 投递：进 cookie / body / header（按落点）
6. 验证：无害命令（id / whoami）+ DNSLOG；证明 RCE 即清理
```

**红线**：反序列化 PoC 一律本地影子环境验证后再打目标；上线只跑无害命令，用完即清（`webshell.md` 协议）。