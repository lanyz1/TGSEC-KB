## 十、自动化工具

| 工具 | 用途 |
|------|------|
| Autorize (Burp) | 自动IDOR检测（低权限Cookie重放）|
| AuthMatrix (Burp) | 角色权限矩阵测试 |
| AutoRepeater (Burp) | 自动替换参数重放 |
| Burp Bounty | 自动化扫描规则 |
| GraphQL Voyager/InQL | GraphQL探索与IDOR测试 |
| JWT_Tool | JWT测试与篡改 |
| ffuf/wfuzz | ID枚举fuzz |
| Arjun | 参数发现（隐藏ID字段）|
| **31n3/BolaScan/APIsec自研** | 自动化BOLA检测 |
| **nuclei + custom templates** | IDOR批量模板扫描 |
| **UUID分析工具** | UUIDv1解码/熵分析（见第六章）|
| **hashids库** | 编码ID逆向（见6.5）|
| **HTTPie + jq** | 快速响应对比diff |

### 10.1 Autorize使用（高级）
```
1. 配置低权限用户Cookie
2. 用高权限用户正常浏览（抓全请求）
3. Autorize自动以低权限Cookie重放
4. 分析：200+内容差异=IDOR
5. 进阶：设置"对比模式"，忽略无关头字段，聚焦body
6. 结合AutoRepeater替换资源ID
```

### 10.2 AuthMatrix使用
```
1. 配置多角色Cookie（admin/user1/user2/unauth）
2. 定义角色与请求矩阵
3. 自动检测垂直/水平越权
4. 进阶：跨租户场景配置多个租户会话
```

