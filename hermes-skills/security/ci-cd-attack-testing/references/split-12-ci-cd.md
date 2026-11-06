## 十、CI/CD 漏洞情报速查表

### 10.1 Jenkins
| CVE | 描述 | 影响/评分 | 备注 |
|-----|------|----------|------|
| CVE-2024-23897 | CLI args4j expandAtFiles 任意文件读取→RCE | 2.441及更早/LTS 2.426.2及更早，9.8 | KEV 在野利用 |
| CVE-2024-52549 | Script Security 权限检查缺失(文件探测) | 中危 | |
| CVE-2024-52550/52551 | 已撤销脚本可重建/重启(绕过审批) | 高危 | |
| CVE-2024-52553 | OIC Auth 会话固定→社工拿管理员 | 高危 | |
| CVE-2022-46751 | IvyTrigger 捆绑 Ivy XXE | 高危 | |
| CVE-2018-1000861 | Script Security 沙箱绕过 RCE | 高危 | 经典 |
| CVE-2017-1000353 | CLI 反序列化 RCE | 9.8 | 经典 |

### 10.2 GitLab
| CVE | 描述 | 影响/评分 | 备注 |
|-----|------|----------|------|
| CVE-2023-7028 | 任意用户密码重置(含管理员) | 16.1~16.7受影响，7.5 | 2FA缓解 |
| CVE-2023-2825 | 任意分支合并权限绕过→RCE | 9.6 | |
| CVE-2021-22214 | CI lint 未认证 SSRF | 7.0 | 内网探测 |
| CVE-2021-22205 | 未认证 RCE(Markdown上传) | 10.0 | 经典打点 |

### 10.3 GitHub Actions / ArgoCD / 其他
| CVE/事件 | 描述 | 备注 |
|----------|------|------|
| CVE-2025-30066 | tj-actions/changed-files tag篡改→secrets内存窃取 | KEV，23000+仓库受影响 |
| CVE-2024-37152 | ArgoCD /api/v1/settings 未认证访问 | 组合利用可接管集群 |
| CVE-2024-40634 | ArgoCD /api/webhook 未认证 DoS | |
| CVE-2023-22482 | ArgoCD OIDC audience 未校验 | 伪造 token 提权 |
| CVE-2023-22736 | ArgoCD 命名空间授权绕过 | |
| CVE-2023-42793 | TeamCity 未认证 RCE | 9.8，广泛在野 |
| CVE-2021-22205 | GitLab 未认证 RCE | 打点经典 |
| CVE-2019-16097 | Harbor 任意管理员创建 | 旧版 |

> 完整列表以各官方安全公告为准，测试前先核对目标版本与最新公告。

