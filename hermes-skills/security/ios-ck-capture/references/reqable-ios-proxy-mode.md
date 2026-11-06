# Reqable iOS 抓包 + 代理链路（实测 2026-08，iPhone 12 / iOS 18.6.2 / 国内网络）

## 目标
无越狱 iPhone 上抓 TikTok web Cookie（Safari 登录态），需要科学上网才能访问 TikTok 的场景。

## 完整链路（唯一实测可行的组合）
```
手机WiFi手动代理(127.0.0.1:9000)
  → Reqable「代理端口」模式(9000，不开VPN)
  → Reqable 二级代理(127.0.0.1:1082，HTTP)
  → Shadowrocket「共享代理」(HTTP，把机场SK5节点转成本地HTTP)
  → 机场节点 → TikTok
```

## 为什么不能简化（每个坑都是实测撞出来的）
1. **新版 Shadowrocket 无抓包功能**（HTTP Capture/MITM 被砍）——设置里只有 语言/高级/隧道/权限/更新/其它。别找。
2. **Reqable 二级代理只支持 HTTP**——直接填机场 SOCKS5 节点 = "不支持的代理格式"。必须先把 SK5 节点转成 HTTP（用 Shadowrocket 共享代理）。
3. **iOS 单 VPN 限制**：Reqable 若用「记录模式(VPN)」启动，Shadowrocket 的 VPN 被顶掉 → 共享代理端口(1082)随之失效 → 上游断 → TikTok 打不开。
   - 解法：Reqable 切「代理端口(9000)」模式（记录模式 VPN 开关关闭），只开本地 9000 端口不占 VPN；Shadowrocket 保持 VPN 连接。
   - Reqable 界面里「记录模式(VPN)」与「代理端口(9000)」是两个独立开关。
4. **WiFi 手动代理「路由器」字段必填**（留空不能保存）→ 填 `127.0.0.1`（与服务器一致）。
5. **TikTok 网页跳 App**：检测到设备装了 TikTok App → 强制跳转。Safari 点地址栏「aA」→「请求桌面网站」，桌面版不跳。
6. 多层代理网速慢是正常的，能加载就行；抓包不需要快。
7. 搜不到 `beat` 请求不要卡住——**任意 www.tiktok.com 请求都带完整 Cookie**，直接复制任意请求的 Cookie 即可（token/beat 只是最典型的那个）。
8. Reqable 术语：二级代理=上游代理；SSL代理=HTTPS 解密（必须开）；Bypass Apple 保持开（不抓 Apple 域名）；认证默认不开。

## Reqable 配置清单
- 证书：Reqable「安装证书」→ 描述文件安装 → 设置→通用→关于本机→证书信任设置→开开关（必须，否则 HTTPS 抓不到）
- SSL代理：开
- 二级代理：服务器 127.0.0.1、端口=Shadowrocket共享代理端口、认证留空、模式「绕行模式」（列表留空=全部走代理）
- 记录模式(VPN)：关；代理端口(9000)：开

## Shadowrocket 配置清单
- 设置 → 共享代理(Share Proxy) → 开 → 协议选 HTTP → 记端口（如 1082）
- 认证：不开
- 节点保持连接（VPN 图标在）

## 抓取步骤（用户侧）
START(代理端口模式) → Safari tiktok.com（桌面版）→ 登录测试小号 → 逛两下 → Reqable 列表 www.tiktok.com → 任意请求 → 请求 → Cookie → 长按全选复制

## 批量生产方向（未实施）
- 每台设备独立住宅 IP（NAT 不可入站）→ 平台无法直连设备 IP
- 需要设备隧道（企业签名 App 主动出站连平台，平台借道出站）
- 小批量（≤20 台）现有链路够用；tokenBeat 走账号代理 + 低频刷新
- 平台侧已就绪：tokenBeat 支持传代理、绑定流程、/api/tiktok/videos/sync
