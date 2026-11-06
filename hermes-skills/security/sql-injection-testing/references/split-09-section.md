## 八、工具链与自动化

### 8.1 工具选型
| 工具 | 用途 |
|------|------|
| sqlmap | 自动化注入检测利用（首选）|
| Burp Suite | 手动测试/代理/Repeater |
| NoSQLMap | MongoDB/NoSQL注入 |
| SQLiPy (Burp插件) | Burp集成sqlmap |
| Hackvertor (Burp插件) | 编码标签化绕过 |
| Gopherus | Gopher协议SSRF→SQLi |
| tplmap | SSTI模板注入（非SQL但需联动）|
| NoSQLAttack | NoSQL注入 |

### 8.2 Burp插件辅助
- **Hackvertor**：使用`<@hex_entities>`、`<@urlencode>`、`<@unicoder>`标签动态编码
- **Burp Collaborator**：OOB外带数据接收（DNS/HTTP）
- **Active Scan++**：二阶注入/高级绕过
- **JSON Web Tokens**：JWT注入场景

### 8.3 自定义Tamper编写思路
1. 确定目标WAF拦截的关键字符/关键字
2. 编写字符级替换函数（空格/引号/关键字）
3. 添加版本探测逻辑，针对版本加载特定替换
4. 使用`__priority__ = PRIORITY.HIGHEST`确保优先级
5. 参考ByPassTamperPlus：按数据库版本定制、集成该版本独有函数做语法变形

