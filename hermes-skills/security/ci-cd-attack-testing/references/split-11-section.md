## 九、典型案例复盘（红队视角）

### 9.1 tj-actions/changed-files 供应链攻击（CVE-2025-30066）
```
# 时间线（2025.3）:
# 1) 攻击者先攻陷 reviewdog/action-setup 项目（注入后门）
# 2) 利用被攻陷的 PAT(@tj-actions-bot) 篡改 tj-actions/changed-files
#    的版本 tag，全部重定向到一个恶意 commit（0e58ed8...）
# 3) 恶意脚本: 从 Runner.Worker 进程内存 dump 所有 CI/CD secrets，
#    双重 base64 编码绕过 GitHub secret masking，打印到公开构建日志
# 4) 影响: 23,000+ 仓库引用（实际泄露 secrets 的 218 个）；
#    最初目标疑为 Coinbase 开源项目 agentkit（借其 CI 投毒/发布）
# 5) 已入 CISA KEV 目录
# 红队启示:
# - 攻陷"知名 Action 维护者账户"= 一键投毒数千仓库
# - 固定 action 到 commit SHA 可缓解；攻击者选择篡改 tag 而非 commit
# - secrets 在构建内存中是明文，内存 dump 是 CI 凭据窃取的通用手法
# - 开源 CI 供应链 = 以最小投入换取最大影响面的攻击向量
```

### 9.2 SolarWinds 类更新机制投毒
```
# 手法: 攻陷软件厂商的构建/发布通道（而非代码仓库）
# 特点: 合法签名+合法发布渠道 → 安全软件/监控软件用户全中招
# 红队迁移到 CI/CD: 攻 CD/制品库/签名密钥持有者，替换"受信任更新"
# 检测规避: 保持原版本号/签名，仅替换内容
```

### 9.3 依赖混淆实战（Alex Birsan 2021）
```
# 过程: 枚举目标内部包名（npm view 确认公共源无同名）→ 抢注 → 
#       内部 CI 构建自动安装 → 恶意 postinstall 执行 → 回连
# 结果: 苹果/Microsoft/特斯拉等 35+ 厂商内网 RCE/数据回传
# 红队要点: 依赖混淆不需要任何代码库权限——只需要"知道内部包名"
# 侦察重点: 公共代码仓库中的 import/require/pom.xml/requirements.txt
```

### 9.4 Jenkins 在野利用链（CVE-2024-23897）
```
# 事件: 2024 公开后数小时内即被批量利用（KEV 收录、EPSS 100%）
# 利用链: 未认证 CLI 文件读取 → 读密钥/用户 → 伪造 Remember me cookie/
#         配合 Script Console → RCE → 内网横向
# 红队要点: 公网暴露的 Jenkins 是"零门槛"入口；先探测再打
```

### 9.5 攻击链串联示范（一个入口→全供应链）
```
# 场景: 公网暴露的 GitLab 存在 CVE-2023-7028
# 链: 密码重置拿管理员 → 读 CI/CD variables(云AK) → 篡改 CI job 注入后门 →
#     云横向(联动cloud-security-audit) → 拿生产 → 顺藤摸瓜回 GitLab 供应链
# 核心原则: 每攻陷一环立即"播种"（后门CI任务/影子Runner/镜像后门），
#           保证即使被清理也有备选持久通道
```

