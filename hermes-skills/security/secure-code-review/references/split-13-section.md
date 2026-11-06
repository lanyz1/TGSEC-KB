## 十二、修复建议

### 12.1 通用修复模式

```
- SQL 注入 → 参数化查询/ORM 预编译；MyBatis 用 #{} 弃 ${}；拒绝拼接
- 命令注入 → 参数数组形式（不经过 shell）；白名单命令与参数；最少权限用户
- 反序列化 → 强类型白名单/ObjectInputFilter/TypeNameHandling.None；禁用危险框架默认值
- SSRF → 协议白名单（http/https）+ DNS 解析后 IP 二次校验 + 内网段拦截 + 302 跟随限制
- 路径遍历 → realpath/normalize + 前缀校验 + 拒绝绝对路径/../；随机文件名
- XXE → 禁用 DOCTYPE/外部实体（disallow-doctype-decl + external-general-entities=false）
- XSS → 输出编码按上下文；CSP 非严格模式一律加 nonce/hash
- 越权 → 服务端强制 RBAC + 行级数据所有权校验（资源归属=会话主体）+ RLS
- 竞态 → 数据库原子操作/分布式锁/幂等键；状态机加锁流转
- 密钥 → 移除明文；接密钥管理（Vault/KMS）；轮换受影响凭据
```

### 12.2 框架层加固

```java
// Spring：全局异常统一处理，禁止堆栈外泄
// Fastjson：ParserConfig.getGlobalInstance().setSafeMode(true)
// Jackson：activateDefaultTyping 禁用 / 自定义白名单
// SnakeYAML：yaml.loadAs(input, TargetClass.class) 替代 load()
```
```go
// 禁用 cgo 提权面；构建时 -buildmode=pie -trimpath
// 所有外部输入统一过 validator（go-playground/validator）
```
```js
// 冻结 Object.prototype：Object.freeze(Object.prototype)
// 安全解析：JSON.parse 替换 eval；深拷贝用 structuredClone 而非手写 merge
```
```php
// 类型比较全部 ===；文件包含白名单映射；phar:// 限制
// ini: disable_functions=system,exec,shell_exec
```
```csharp
// BinaryFormatter 弃用（.NET 9 已移除）；Json.NET 禁 TypeNameHandling
// DataProtectionProvider 管理机器密钥
```

### 12.3 依赖与供应链修复

```bash
# 升级 EOL 组件（Log4j 1.x / Fastjson 1.x → Fastjson2 / 老 Jackson）
# 修复命令示例
pip install --upgrade requests
npm update lodash minimist
go get -u github.com/xxx/yyy

# lockfile 完整性校验（CI 中）
npm ci --ignore-scripts            # 跳过安装钩子（防御 install 脚本投毒）
pip install --require-hashes -r requirements.txt
go mod verify

# 恶意包应急处置：定位受影响主机 → 视为失陷 → 清理 → 轮换凭据 → 审计后续动作
```

### 12.4 修复验证

```bash
# 修复后复扫（应清零对应规则告警）
semgrep scan --config=semgrep-rules/taint-sqli.yaml --baseline-commit HEAD~1 ./src
# 回归测试：原 PoC 应失效；功能测试通过
# 将修复写入安全编码规范，防止回归
```

