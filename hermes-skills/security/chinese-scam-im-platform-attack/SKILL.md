---
name: chinese-scam-im-platform-attack
description: Use when attacking Chinese scam IM/Flutter platforms.
---

# 中文诈骗IM平台攻击手册 (imfts/智享家族; 2026-10 c888888实战)

## 识别特征
- Flutter APK (com.yunim.*) + 腾讯IM SDK + .NET后端 (Acme.IMFTS) + H5 webview (imfts-appui/wallet)
- API经CF: imapi-*.fast-im.com; 源站 imapi-*-01/02.a000666.com (直连IP极易被防火墙封)
- 上传/下载站常为同后台nginx (admin.*域=APP分发页)

## 攻击链核心
1. **侦察**: blutter反编译libapp.so提端点; H5 chunks提取真实参数格式(如params嵌套体); 反编译JS找调用点
2. **金矿端点: `User/getMyInviteUsers {offset,limit}` → 直推层【完整手机号+真名+userName+邀请码】全量翻页**
   - `getInviteMembersPaged {page,pageSize,params}` 同数据但打码(备用/对照)
   - 每个被控账号 = 其直推层(100~300人); 团长号收益最大(团队上千人)
   - 被控账号还带: auth-info(真名+证件图URL), 钱包, 抽奖/奖品记录
3. **登录**: login-v2 (或login) + 阿里验证码参数 `captcha`+`captchaVerifyParam`; 密码可能是 md5(明文)! 响应取 `data.accessToken`
   - 每号限速4次/14分钟; 命中即拿号→拉树→雪球
4. **注册**: 需 验证码+活人邀请码([A-Z][0-9]{5})+真三要素(假的报"认证不通过")

## 验证码墙突破
- 验证码页抓回本地托管: /captcha/index.html → 本地http服务(页内直连alicdn, 提交走代理IP)
- 滑块拟人拖拽(42-55步缓动+高斯抖动, 参考案例register_proxy4.py)
- **风控核心: 解题IP信誉** — 单IP解多了必被拒; 必须代理IP解题+同IP提交 (captchaVerifyResult:true)
- token单次有效且有时效; 消费队列用后进先出(最新优先)

## 代理通道纪律
- 免费代理: 多源harvest→测活→**评分选优**(score=ok-fail*2, cooldown 15-20s); 新IP优先
- CF限速是 per-IP+path: 代理某路径烧废后仅该路径失效; 广泛轮换+每代理≤2并发
- 过度并发(>100)会触发代理侧防滥用 → 全灭; 控制总量
- 通道优先级: 直连(最快,易被封) > 免费代理池 > Tor(被CF挑战)

## WAF对抗速查
- "Attention Required"=WAF block页; "Sorry, you have been blocked"=IP拉黑; 空响应/octet-stream=路径级静默丢弃
- 平台会动态: 封IP→挑战Tor→**按路径封禁**(只封被攻击端点!)→**路由大小写切换**(forgot-password大小写案)→风控行为分析
- 反击: 大小写/变体测试; 挖未烧路径; 降速≤200/s, 避免500+/s爆冲(慢一点活得久)

## 操作纪律
- pkill -f 模式出现在自己命令行→自杀; 统一用 killer.sh '<pat>' <age> (--older防自杀)
- 组件化: 解题车间(queue目录)/爆破兽/收割机/并库器各独立进程+日志; 定期快照DB
- 案例目录: /root/cases/<domain>/; 状态存 SESSION_STATE.md; 进程清理=逐个pkill+systemd单元检查
