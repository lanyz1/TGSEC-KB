## 二、被动侦察全维度（OSINT·企业/人员/泄露）

### 2.1 Whois 与注册信息
```bash
# 基础查询
whois target.com
whois target.com | grep -E "Registrant|Email|Phone|Name Server"

# RDAP（新一代标准化接口，支持结构化输出）
curl -s https://rdap.org/domain/target.com | jq .
curl -s https://rdap.arin.net/registry/entity/ORGNAME | jq .

# 在线数据源
# who.is / whois.domaintools.com（历史Whois） / viewdns.info / rdap.org
# 反查：同注册人邮箱/名称反查全部域名（Domaintools Reverse WHOIS、whoisxmlapi）
```

**关键动作（红队必做）：**
- **注册邮箱/电话反查**：`@"域名注册邮箱"` 在空间引擎/WhoisXML 中反查同一主体其他域名
- **历史 Whois**：注册人变更记录可暴露目标真实身份、旧联系邮箱（可入社工库）
- **隐私保护识别**：whoisguard/domainprivacy 等隐私服务 + 历史记录可还原真实注册人

### 2.2 企业工商信息与 ICP 备案（国内攻防核心）
```bash
# 备案查询（ICP/IP地址/域名信息备案管理系统）
https://beian.miit.gov.cn
# 备案号反查：同一备案主体下全部域名 → 扩展资产
site:beian.miit.gov.cn "公司名"
# 工具：无影 多引擎备案反查；ICP备案查询API（如 fofa/hunter 集成）

# 企业工商信息
# 天眼查 / 企查查 / 爱企查 / 国家企业信用信息公示系统(gsxt.gov.cn)
# 重点维度：
#  - 对外投资/控股子公司（>50% 可能内网互通）
#  - 分支机构、关联企业（品牌/法定代表人关联）
#  - 软件著作权（登记名可反查系统名→搜"系统名"找入口）
#  - 商标、专利（暴露产品线、新技术方向）
#  - 年报/联系方式（泄露邮箱格式、电话段）
```

**实战要点：**
- 攻防演练中"备案号→主体→所有备案域名"是扩展攻击面的第一梯队手段
- 子公司/控股公司资产经常与母公司内网互通或共用 VPN/SSO，是横向突破口
- 软件著作权名称 = 系统名称，用 `site:目标.com "系统名"` 或空间引擎直接定位该系统

### 2.3 搜索引擎 Dorks
```
# 通用语法（Google/Bing/百度/360 语法略有差异）
site:target.com inurl:admin|login|dashboard
site:target.com filetype:sql|bak|conf|env|log|zip|rar
site:target.com inurl:.git|.svn|.DS_Store|phpinfo.php
site:target.com "Index of /"
site:target.com "password"|"api_key"|"aws_secret"|"accessKeyId"
site:s3.amazonaws.com "target.com"
site:pastebin.com "target.com"
site:*.target.com -www

# 人员/组织
"@target.com" site:linkedin.com            # 员工邮箱格式
"@target.com" site:github.com              # 员工GitHub
"公司名" "工资表|通讯录|花名册" filetype:xls|doc|pdf   # 公示文档泄露

# 多引擎联动（国内目标必须覆盖百度/搜狗/360）
# 百度：site:target.com 后台 | 管理 | 测试
# 搜狗微信搜索：搜索目标公众号/小程序泄露信息
```

### 2.4 代码托管平台泄露（GitHub/GitLab/Gitee）
```bash
# GitHub 搜索（2023+ 需登录；Gitee 无需）
"target.com" password|secret|api_key|token
"公司名" 密码|密钥|内网|数据库
filename:.env target
filename:wp-config.php|config.php target
filename:.git-credentials target
path:.ssh/id_rsa target
filename:config.json password

# Gitee（国内开发者常忽略安全）
# gitee.com 搜索 "公司名" + 敏感关键字
# GitLab 自建实例：常见 8080/9090 端口 + /explore 公开项目

# 工具链
- gitdorks_go / GitDorker / GitRob / GitGot
- trufflehog / gitleaks（深扫历史提交中的密钥）
- GitHack / dvcs-ripper（提取泄露的 .git/.svn 完整源码）
- shhgit（实时监控全球公开代码提交）
```

### 2.5 网盘/文库/公开文档泄露（国内特色）
```bash
# 网盘搜索（员工常传敏感资料）
# 凌风云 / 猪猪盘 / 云盘狗 / 小马盘 / 超能搜
# 关键词：公司名+拓扑图/台账/密码/账号/花名册/巡检表

# 文库泄露
# 百度文库 / 搜文库 / 360文库
# 关键词：公司名+运维手册/实施方案/投标文件（含拓扑、IP、账号）

# 其他公开文档
# 招投标网站（中国政府采购网等）：实施方案常含网络拓扑、系统清单、IP规划
# 官网"供应商/合作伙伴"栏目 → 供应链线索
```

