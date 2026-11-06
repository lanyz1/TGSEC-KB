# iOS 手机端手动抓包实测死路全记录（2026-08-29，推翻 SKILL.md 旧"可行方案"）

## 实测过程与结论
目标是 iPhone 12（iOS 18.6.2）上抓 Safari 登录 tiktok.com 的 web Cookie。尝试了 Reqable / Shadowrocket / WiFi 手动代理全组合，全部失败，结论如下（每条均实测）：

### 1. iOS 同一时间只允许一个 VPN 激活
- Reqable 点 START（VPN 记录模式）→ **Shadowrocket 的 VPN 被系统顶掉** → Shadowrocket 隧道断 → 它的「共享代理」（Share Proxy，监听如 1082）也随之失效 → Reqable 二级代理(127.0.0.1:1082)连不上 → **tiktok.com 打不开**（实测：Reqable VPN 起来后 TikTok 无法访问）
- 反向（Shadowrocket 连着）→ Reqable 无法以 VPN 模式启动抓包

### 2. ★iOS WiFi 手动代理指向 127.0.0.1（本机回环）被系统忽略
- 判别测试：WiFi 手动代理服务器填 127.0.0.1、端口改成**不存在的 9001** → Safari 打开 tiktok.com **仍能正常上网** = 流量根本没走代理（一直走 Shadowrocket VPN）→ 代理配置被 iOS 忽略
- 推论：Reqable「代理端口(9000)」模式（依赖 WiFi 代理指本机）同样无效
- **iOS WiFi 代理只对"局域网其他主机"生效**（指电脑 IP 可行——电脑端抓包方案的基础）

### 3. Reqable「二级代理」（=上游代理）只支持 HTTP
- 界面字段就叫"HTTP代理服务器地址"；填机场 SOCKS5 节点 → 报 **"不支持的代理格式"**
- 除非机场同时提供 HTTP 代理端口，否则"Reqable VPN + 上游机场节点"方案也走不通

### 4. Shadowrocket 新版（App Store 美区）已砍 HTTP 抓包
- 设置主列表只有：语言 / 高级(延迟测试方法·TCP、小组件、捷径、诊断、外观) / 隧道(按需求连接、隧道、代理、TCP、UDP) / Tailscale / 权限(位置·通知·剪贴板) / 更新(配置·模块·订阅·GeoLite2) / 其它(VPN提醒·温和策略机制)——**没有 HTTP Capture/MITM/HTTPS 解密条目**，别浪费时间找

### 5. Reqable 抓 HTTPS 的完整必要条件（若未来环境变了还有用）
- 「SSL代理」= HTTPS 解密开关：须**新建规则**填域名 `tiktok.com` + `*.tiktok.com`，模式选**拦截(Intercept)**（绕行=Bypass = 不解密）
- 证书两处（缺一不可）：① 设置→通用→VPN与设备管理 → 安装描述文件；② **设置→通用→关于本机→证书信任设置 → 打开开关**（描述文件装完≠信任，是两个页面）
- iOS WiFi 手动代理「路由器(Router)」字段留空不能保存 → 填与服务器相同地址可保存
- Reqable「记录模式(VPN)」与「代理端口(9000)」是**两个独立开关**：代理端口模式 = VPN 关 + WiFi 代理指向 9000

### 6. 设备本身限制
- iPhone 12（A14）→ checkm8/palera1n 越狱只支持 A11 及以下 → **无越狱**
- TikTok App HTTPS 证书固定 → 无越狱无法抓 App 数据
- Safari web 流量无证书固定（理论上可抓）但**没有不依赖 WiFi 代理的抓包入口**

## 正确方向（不要再走手机手动抓包）
1. **企业签名抓包 App**：NEPacketTunnelProvider 自建隧道（不依赖 WiFi 手动代理）→ $299/年 Apple Developer Enterprise
2. **比特浏览器扩展采集**（新路线）：MV3 扩展内置比特窗口，详见 tiktok-data-collection skill 的 references/bitbrowser-extension-collection.md
3. 若只是验证平台链路（不追求设备 IP）：局域网电脑抓包（WiFi 代理指电脑 IP + 电脑科学上网）
