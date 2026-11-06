## 八、开发者终端与个人环境（初始访问补充面）

### 8.1 开发者机器作为跳板
```
# 开发者 = 代码库高权限 + CI 高权限 + 云控制台访问
# 初始访问: 钓鱼（开发者更易中招技术主题钓鱼）/浏览器会话/凭据填充
# 上线后: 提取 git 凭据(Git Credential Manager)、SSH agent、浏览器 cookie
```

### 8.2 IDE/插件投毒
```
# VS Code 扩展市场仿冒扩展（恶意 telemetry/后门）
# 插件安装即执行: 恶意扩展在 developer 机器上全权限
# 脚手架/模板: create-xxx 模板被替换 → 新项目自带后门
# 代码片段/格式化工具链劫持
```

### 8.3 Git 凭据与 SSH agent 窃取
```
# Windows: Credential Manager 中的 git 凭据（cmdkey /list）
# ~/.git-credentials / ~/.config/gh/hosts.yml（gh CLI token）
# ~/.ssh/id_* + known_hosts（SSH 免密通道）
# GPG 签名密钥（伪造提交身份）
```

### 8.4 开发者浏览器会话
```
# 代码托管平台 session cookie → 直接接管仓库操作
# 云控制台会话 → 基础设施控制
# 密码管理器 → 全凭据
# 红队建议: 开发者终端目标要"一次性拿全"再出手，避免打草惊蛇
```

