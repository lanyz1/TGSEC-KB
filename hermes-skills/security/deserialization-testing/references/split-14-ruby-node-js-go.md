## 十三、Ruby / Node.js / Go 反序列化

### 13.1 Ruby Marshal / YAML / JSON
```ruby
# Marshal.load（最危险）：二进制格式，攻击者可控对象图
Marshal.load(File.binread("evil.marshal"))
# 已知链：Gem::SpecFetcher → Gem::Requirement → Gem::Package::TarReader → Runtime（2024 公开）
#        Universal Deserialisation Gadget for Ruby 2.x-3.x（universaldg/rubygems）
# YAML（Psych）：YAML.load / YAML.unsafe_load 危险
YAML.load("--- !ruby/object:Gem::Installer\ni: a")
# JSON create_additions：JSON.parse(json, create_additions: true) 可实例化任意带 json_create 的类
# 检测指纹：Marshal 流以 \x04\x08 开头
```

### 13.2 Node.js 反序列化
```bash
# node-serialize / serialize-to-js：函数体被序列化为字符串，反序列化时 eval 执行
# 特征：_$$ND_FUNC$$_function(){return process.mainModule.require('child_process').execSync('id');}()
# 利用：常见于"对象序列化后存 Redis/DB，再从请求数据还原"的 RCE 场景
# 工具：node-serialize-exploit；审计关键字：unserialize|serialize|serialize-to-js
# 其他：js-yaml unsafelyLoad / js-yaml load 旧版本（!!js/function 标签可 RCE）
#      proto 污染 → 命令执行（__proto__.NODE_OPTIONS / child_process 参数投毒）
```

### 13.3 Go 反序列化
```
- encoding/gob：仅解码已注册具体类型，默认安全；但反序列化后对象方法调用仍可能触发副作用
- 关注点：应用自实现"反序列化→反射调用"逻辑（如 JSON → mapstructure → 动态方法调用）
- Go 生态反序列化 CVE 少，主要风险在"业务逻辑层反射"与跨语言互操作（Java/Python 服务传递序列化数据）
```

