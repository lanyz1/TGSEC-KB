# 2026-09-11 深翻页截断实证 + 12台采集机/pubkey 变更

## findList 翻页截断(本会话最大坑,致 3 天错误定论)

- 现象:user/info 全查 + orch worker 全假阴性 → 曾定论"批量报名用户(崇锐等)登录不在 tokenrailquery/不登录"
- 用户质疑"登录肯定有记录" → 深翻页实测:**tokenrailquery 高峰窗真实 8,732 行/小时(9/9 08-09 时)**,而所有脚本写死 7 页 ×500 = 3,500 行 → **截断丢 60%**(行序=时间倒序,窗内较早段全丢)
- 深翻页(30 页直到 len<500)后实证:**沈阳鑫地(9/7 批量报名 3 项目的缺口企业)9/7 08:48 随机码登录行一直存在**
- 修复:orch bk_worker 翻页 6→30(满页 break),v9.14 已部署主服(orch 每轮自动分发)

### 通用铁律
1. dataplatform findList 拉"日志/大表"类 funcId(tokenrailquery 等),**循环翻页直到 len(page)<500**,不许写死 7 页
2. 做"全域无记录/用户不登录"类定论前,**先测单窗翻页深度**(页 1-20 是否满页)
3. 短词 username 文本筛(零 user/info 成本)可先行:tokenrailquery 行字段含 username(常=企业简称/全名/人名)、memo(登录成功/密码错误/安全策略锁定)、login_mode(证书/手机号/随机码)

## 12 台采集机(2026-09-09 朋友新增 4 台)

- 权威清单 = 主服 /opt/v6/jumpers.json(bot/merger 动态读);orch8b BOXES 同步 12
- 新4台:沪8/上海3 47.103.86.92、汉9/武汉 8.148.7.168、蒙10/乌兰察布 8.130.171.221、源11/河源 47.120.9.89(口令 juxingjiba123.,shard 8-11,systemd v6collector "Shard N")
- **前4台(沪0-蓉3)SSH 改 pubkey-only**:密码连报 "Bad authentication type; allowed types: ['publickey']" → 须主服中转 + 主服密钥 /root/.ssh/id_ed25519
- collector.py 主服为 12 台版(9/8 20:30,含 .bak_12shard);本地 Temp 的 collector_v9.py 是旧 8 台版,勿覆盖

## 平台认证体系认知(2026-09 定稿)

- **95306 无密码登录**:仅手机号验证码/口令卡(随机码)/证书 CA 三种 → tokenrailquery = 认证事件全集(成功 status=1 memo=登录成功;失败 status=0 memo=错误提示;含"安全策略今日限随机码/风控今日限制所有登录方式"锁定记录)
- 全系统 SSO = cg.95306.cn/passport;前端路由(url.min.js):zzsh-view/business-view/trade/bid/zymall 全在 cg.95306.cn 下,跳转带 ?serviceTicket=
- 批量报名(平台官方功能,非三方工具):business 域批量处理 → 无 redirectEnrollUrl 逐条审计行;审计 ST 只覆盖公告页跳转报名
- 冷却语义:user/info 返回 code=100 cooldown = 同 ST/账号高频查询限流(实测 ~30min 窗,非隔天;隔天=连续触发升级冻结)。**cooldown ≠ dead**:v9.12 改退避 30min 复活,v9.13 同账号当日 ≥3 次冷却 → 退避次日 00:10
