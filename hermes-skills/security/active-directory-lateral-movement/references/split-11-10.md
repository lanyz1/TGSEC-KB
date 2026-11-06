## 10. 检测与防御

### 10.1 关键攻击的检测信号

| 攻击 | 关键日志/事件ID | 检测特征 |
|------|----------------|---------|
| Kerberoasting | 4769 (TGS请求) | 单用户短时间内请求大量TGS + RC4-HMAC加密 |
| AS-REP Roasting | 4768 (TGT请求) | 无预认证的TGT请求(异常) |
| Pass-the-Hash | 4624 (登录) | 登录类型3(网络)+无4648(明文) |
| Golden Ticket | 4769/4768 | 票据有效期异常长/异常SID History/PAC异常 |
| DCSync | 4662 (目录访问) | 非DC账户调用复制权限(1131f6aa/1131f6ad) |
| DCShadow | 4662 + 5137 | 新DC注册+配置命名空间修改 |
| NTLM Relay | 4624 + 4776 | 同源认证跨多目标/异常认证源 |
| ADCS ESC | 4886/4887 (证书) | 异常证书申请+非预期SAN |
| RBCD | 4662/5136 | msDS-AllowedToActOnBehalfOfOtherIdentity 修改 |
| PetitPotam | 4624 | DC向异常主机发起认证 |

### 10.2 纵深防御矩阵

| 防御层 | 措施 | 防御攻击 |
|--------|------|---------|
| 协议层 | 强制SMB签名 + LDAP签名 + Channel Binding(EPA) | NTLM Relay |
| 认证层 | 禁用NTLM(仅Kerberos) + 启用PAC签名校验 | PtH/Golden Ticket |
| 账户层 | 所有账户启用预认证 + 服务账户用gMSA + 强密码 | AS-REP/Kerberoasting |
| 委派层 | 关闭非约束委派 + 启用PAE(Protected Users) | 委派攻击 |
| PKI层 | 审计证书模板 + 关闭ADCS HTTP接口 + 安全模板设计 | ADCS ESC1-8 |
| 权限层 | 收敛ACL(Tier模型) + 限制MachineAccountQuota | ACL滥用/RBCD |
| 监控层 | 部署EDR + SOC关联4769/4662/4887 | 全域攻击检测 |
| 凭据层 | krbtgt定期双轮换 + LAPS管理本地管理员密码 | Golden Ticket/横向 |
| 网络层 | 分区(Tier 0 DC/Tier 1服务器/Tier 2工作站) | 横向移动 |

### 10.3 Tier 管理模型

微软推荐的分层模型，限制凭据跨层流动：

```
Tier 0 (域控)    — DC/AD/CA/虚拟化宿主  — 绝不登录Tier1/2
Tier 1 (服务器)   — 应用/数据库服务器      — 绝不登录Tier2
Tier 2 (工作站)   — 用户终端              — 可登录任意，但管理员凭据不进入
```

**核心原则**：高Tier的管理员凭据**绝不**在低Tier主机上输入(否则被LSASS提取)。这是阻断"从工作站横向到DC"的根本防御。

---

