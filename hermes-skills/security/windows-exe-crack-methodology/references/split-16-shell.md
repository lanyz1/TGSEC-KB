## 攻作者服务器(客户端破解后, 用户可能要求打服务器/抢 shell)
Electron/采集工具破解后, 作者服务器往往有 admin 弱口令 + Swagger 泄露, 数据层可全通, 但 RCE 通常不可达。
- **顺序**: 扫 swagger(v2/api-docs 未授权) → 试 admin/admin 弱口令 → staff/list 类接口拉员工+密码哈希 → 已知明文尝试还原密码加密(客户端 AES key 失败=服务端专用, 止损) → 无 RCE 时交付数据层成果。
- **端口必须走代理真实扫描**(TUN 直连全 OPEN 假象); 安全组常只开业务端口(81/83/19999), 无 SSH/DB。
- **JWT 快速评估**: token 形如 `eyJ0eX...`(HS256) → alg=none 测试 + 常见密钥字典; 破不了=需 hashcat 大字典, 不强攻。
- 管理接口参数格式在 Web 后台 JS 里(桌面客户端不含), 枚举 500 = 存在但参数错, 拿不到格式就放弃。
- 详情: `references/server-attack-surface.md`。


---

