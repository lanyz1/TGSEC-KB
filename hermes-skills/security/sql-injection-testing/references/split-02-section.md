## 一、注入点完整攻击面

### 1.1 参数输入面（Input Surface）
| 位置 | 注入场景 | 检测方法 |
|------|---------|---------|
| URL Query参数 | `?id=1&cat=2` | 单引号/闭合测试、布尔差异 |
| POST Body | 表单、JSON、XML | 修改Content-Type、参数污染 |
| HTTP Headers | User-Agent、Referer、X-Forwarded-For、Cookie | 修改头值注入、日志投毒场景 |
| Cookie值 | session id、user_id、token | 解码后注入、分块注入 |
| RESTful Path | `/user/1/profile` → `/user/1' AND 1=1--/profile` | 路径注入、路径参数污染 |
| JSON字段 | `{"id":1}` → `{"id":"1' AND SLEEP(5)--"}` | 类型混淆（int→string） |
| XML/Soap | XML实体+SQL拼接 | XXE+SQLi组合攻击 |
| 二阶注入 | 注册用户名`admin'--`，后续查询触发 | 持久化数据二次利用 |
| HTTP方法 | `GET/POST/PUT/PATCH/DELETE` | 方法变换、OPTIONS探测 |
| 多参数组合 | `?a=1&b=2` → `a=1'/*&b=*/AND 1=1--` | 参数拆分、注释拼接注入 |

### 1.2 注入类型分类
- **Union注入**：联合查询回显
- **Boolean盲注**：真假条件差异
- **Time-based盲注**：时间延迟差异
- **Error-based报错注入**：数据库错误回显
- **Stacked queries堆叠注入**：多语句执行
- **Second-order二阶注入**：存储后触发
- **Out-of-band外带注入**：DNS/HTTP外带数据
- **Wide-Byte宽字节注入**：GBK等编码绕过`addslashes`
- **HTTP Parameter Pollution参数污染**：多同名字段绕过
- **NoSQL注入**：MongoDB/Redis等非关系型

### 1.3 闭合类型识别
```
数字型: id=1 AND 1=1--
单引号字符串: id=1' AND '1'='1
双引号字符串: id=1" AND "1"="1
括号型: id=1') AND ('1'='1 / id=1") AND ("1"="1
LIKE型: keyword=x%' AND SLEEP(5)--%'
```

