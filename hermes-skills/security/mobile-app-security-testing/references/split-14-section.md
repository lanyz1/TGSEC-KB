## 十三、移动供应链与后端云攻击面

### 13.1 SDK 投毒与恶意库（供应链攻击）
```
1. 恶意/受陷SDK: 
   - EngageSDK案例(2026-04, Microsoft披露): Intent Redirection使同设备恶意App借钱包应用身份
     绕过沙箱 → 3000万+加密钱包面临PII/凭据/资金泄露; 修复版本5.2.1
   - 检测: 审计第三方SDK权限(读取短信/通讯录/无障碍)、对外部输入的Intent转发、收集数据外发域名
2. 依赖混淆(Dependency Confusion): 私有包名与公开npm/Maven重名 → 供应链投毒
3. 依赖漏洞: Quokka 2026: 11% Android/13% iOS存在第三方组件严重CVE, 65% Android存在高危CVE
4. AI生成代码风险(vibe coding): 2027年预计25%缺陷源于AI代码 → 测试时重点验证AI辅助开发的功能
```
```bash
# 供应链审计命令
# 反编译后提取依赖清单
grep -rE "com\.|org\.|io\." output_src --include="*.java" | sort -u | head -50
# 对比已知漏洞库(手工)
# 查看gradle/podfile锁定的版本(如有源码)
# 运行时监控敏感行为(外发域名/权限滥用)
frida -U -f com.target -l monitor.js   # hook Socket.connect 记录所有外连域名
```
```javascript
// monitor.js: 监控外连域名 + 权限敏感调用
Java.perform(function(){
    var Socket = Java.use("java.net.Socket");
    Socket.$init.overload("java.lang.String","int").implementation = function(host, port){
        console.log("[NET] " + host + ":" + port);
        return this.$init(host, port);
    };
    var SMS = Java.use("android.telephony.SmsManager");
    SMS.sendTextMessage.overload("java.lang.String","java.lang.String","java.lang.String","android.app.PendingIntent","android.app.PendingIntent")
        .implementation = function(addr, sc, text, si, di){
            console.log("[SMS] to=" + addr + " text=" + text);
            return this.sendTextMessage(addr, sc, text, si, di);
        };
});
```

### 13.2 移动后端 API 测试（深化）
```
1. 认证与Token: JWT算法混淆(none/HS256密钥泄露)/过期失效/刷新链、OAuth授权码劫持、Token日志泄露
2. 越权(IDOR): 篡改 userId/orderId/resourceId → 横向/纵向越权; 重点测"客户端不可见"的对象ID
3. 参数篡改: 价格/数量/优惠/角色字段重放(抓包改包)
4. 未授权接口: 无鉴权可访问的管理/配置/统计接口; 版本号隐藏接口(/api/v1/admin)
5. 速率限制缺失: 爆破/枚举(验证码、用户ID、优惠码)
6. GraphQL: introspection探测 → 查询嵌套耗尽/批量数据泄露(过度获取)
7. 服务端注入: SQL/NoSQL注入、SSRF(通过图片上传/URL预览功能)
8. 业务逻辑: 支付回调篡改、优惠券叠加、订单状态机绕过、积分盗刷
```
```bash
# GraphQL快速测试
curl -X POST https://api.target/graphql -H "Content-Type: application/json" \
  -d '{"query":"{__schema{types{name}}}"}'    # introspection开启即泄露全部schema
# JWT算法混淆
python3 -c "import jwt; print(jwt.encode({'user':'admin','role':'admin'}, '', algorithm='none'))"
```

### 13.3 云凭据泄露与利用
```
1. 云凭据提取(见9.3): AWS AccessKey/GCP服务账号/Firebase key/阿里云AK
2. 验证与利用:
   - AWS: aws sts get-caller-identity → 枚举S3/EC2/数据库 → 数据下载
   - Firebase: 未安全规则配置 → 直接读取整个实时数据库
   - 云函数: 无鉴权触发器直接调用
3. 存储桶枚举: 域名反查 → 尝试公开读写(acl=public-read)
4. 云资源配置错误: 备份公开、密钥在CI日志、对象存储可写
```

