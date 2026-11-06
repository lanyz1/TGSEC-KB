---
name: ios-ck-capture
description: >-
  测绘引擎·Use when iOS 设备上抓 TikTok web Cookie。
owned: true
tier: ops
pack: survey-skill
---

# ios-ck-capture（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/ios-ck-capture/`

溯源（仅标记）：`hermes/media`

---

# iOS 抓 TikTok web CK（苹果设备农场用）

## 背景
- 苹果设备（iPhone 12 / iOS 18.6.2）无越狱 → TikTok App 采集死路（HTTPS 证书固定）
- 正确路线：**设备 Safari 登录 → 抓 web Cookie → 平台 tokenBeat 验证 + web 采集**（复用现有链路）
- App 用于登录环境/远控展示（向日葵），web 用于数据采集——同账号双登录，数据是账号级的

## 关键坑（实测确认）
1. **新版 Shadowrocket（App Store 版）已砍掉 HTTP 抓包功能**——设置里没有 HTTP Capture/MITM，别浪费时间找
2. **Reqable 的「二级代理」（=上游代理）只支持 HTTP 代理格式**——填 SOCKS5 节点地址报"不支持的代理格式"
3. Reqable 中文术语：「二级代理」= 上游代理；「SSL代理」= HTTPS 解密（必须开才能看到 Cookie）
4. 证书信任设置（设置→通用→关于本机→证书信任设置）必须开，否则抓不到 HTTPS

## 可行方案（PoC 级）：Reqable + Shadowrocket 共享代理
```
Reqable(VPN抓包) → 上游代理 127.0.0.1:端口 → Shadowrocket共享代理(HTTP) → 机场节点 → TikTok
```

### 步骤
1. **Shadowrocket**：设置 → 「共享代理 / Share Proxy」→ 开启 → 协议选 **HTTP** → 记端口（如 1082）；认证默认**不开**；保持节点连接
2. **Reqable**：
   - 先装证书：点「安装证书」→ 下载描述文件 → 设置→通用→VPN与设备管理→安装 → 设置→通用→关于本机→证书信任设置→开开关
   - 「SSL代理」开（HTTPS 解密）
   - 「二级代理」新建：服务器 `127.0.0.1`、端口 = 共享代理端口、认证留空、模式**绕行模式**（列表留空 = 全部走代理）
3. 点 START 开始调试 → 允许 VPN 弹窗
4. Safari 打开 tiktok.com → 登录**测试小号** → 多逛几个页面（首页/个人主页/点开作品）
5. Reqable 列表搜 `beat` → 打开 `passport/token/beat/...` 请求 → 请求 → Cookie → 长按全选复制

### 批量生产方案（100 台级）
- 每台设备独立住宅 IP（NAT 不可入站）→ 平台无法直连设备 IP 当代理
- 需要**设备隧道**：设备端 App（企业签名）主动出站连平台，平台采集请求经隧道 → 设备住宅 IP 出站
- 小批量（≤20 台）现状链路够用（tokenBeat 走账号代理 + 低频刷新）

## 平台侧现状（已就绪，无需改动）
- tokenBeat 验证（verifyTikTokCookie 支持传代理）
- 绑定流程 + /api/tiktok/videos/sync 同步 API
- 采集：服务器 curl SSR（资料）+ 客户端采集（作品）
