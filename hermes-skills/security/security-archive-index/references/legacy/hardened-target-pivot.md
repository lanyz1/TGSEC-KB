<!-- archived from /root/.hermes/skills/security/hardened-target-pivot/SKILL.md on 2026-10-21 -->

---
name: hardened-target-pivot
description: "从前端打后端:榨前端映射+挖兄弟域打最弱站。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/hardened-target-pivot`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/hardened-target-pivot/…')`，不要相对 `references/legacy/` 解析。

# 硬化目标横向扩展 (Hardened Target → Estate Pivot)

**触发词**: 从前端打后端 / 找前端网站 / 兄弟域名 / 主站注册全关 / 免凭据面穷尽 / 目标被 WAF 封死

当**主目标**已经打不动 —— CDN/WAF 挡着、每个后端动作都强制会话、`.git` 被封、免凭据面看似穷尽 —— 不要继续在同一个域上原地消耗出口 IP。
**换维度: 把"这个站"升级成"这个组织的整个 web 资产面",然后打最弱的那个。**

核心洞察: **前端是后端的地图,而组织的其它域通常比主域弱一个数量级。**

## 0. 决策树

```
主目标打不通
  ├─ 1. 榨前端: 静态资源里"写死"了完整后端映射 → 逐条实测是否需要会话
  ├─ 2. 找双实现: 同一功能两套鉴权(JSON vs 纯文本返回)→ 打弱的那个
  ├─ 3. 挖兄弟域: 前端首页 href / 备案号 / 图片域 → 新域名全家桶
  ├─ 4. 子域名枚举: 优先 dev. / test. / shop. / mall. / bbs.
  ├─ 5. 打最弱兄弟站: 开放注册 → 过验证码 → 注册登录 → 合法会话
  └─ 6. 进去后: 枚举 oracle / 上传 triage / RCE payload 边界
```

## 1. 榨前端: 拿到"前端自己声明的后端映射"

**这是本类任务最高价值的一步。** 前端不是黑盒 —— 每个页面的 JS 里都写死了它调哪个文件、带哪个参数。

实战形态(国产 EasyUI/jQuery 后台):
```js
// js_all.js 里的页面加载器 —— 泄露了整站页面名空间
var _tpl = function(r){ var tpl = "tpl/_" + r + '.html?_=' + Math.random(); ... }
var _showPage = function(id, glink, txt){ ... _tpl(glink) ... }

// 每个 tpl/_<name>.html 里写死了后端调用
url:'/data6.php?ac=order.bch.detail'
$.post("/data6.php?ac=order.fh.action", {bch:bch, ord_pch:ord_pch})
```

做法:
1. 把已抓到的 `tpl/*.html`、`js/*.js` 全量 grep `(href|src|action|url)\s*[:=]\s*['"]([^'"]*\.php[^'"]*)`
2. 汇总成 **(文件, ac) 对照表** —— 这就是权威的接口清单,**比猜文件名/猜参数强 100 倍**
3. 再按页面加载器拼出 `tpl/_<名字>.html` 枚举更多页面 → 从每页再榨一轮

**Step 2 的实测判定**: 逐条打这张表,记录返回。
- 全部 `{"err":"-99","err_msg":"登录超时"}` → 会话强校验,**这条路就是死的,立刻停手**(别幻想"再多试几个 ac")
- 出现异常项 → 深挖

## 2. 找"双鉴权实现"并打弱的那个

同一产品常有两套会话校验,返回**格式不同**就是信号:

| 文件 | 会话失效返回 | 含义 |
|---|---|---|
| `data.php?ac=xxx` | `{"err":"-99","err_msg":"登录超时"}` | JSON,主实现 |
| `data6.php?ac=xxx` | `登录超时` 纯文本 | **另一套实现** |

发现格式差异后要系统穷尽弱侧(本轮实测过、可作清单):
- 打印/客户端类的 ac(`sf/ems/jd/zt/xp/yt`)打到弱侧
- **会话变量注入**: `uid` / `userid` / `user` / `kf_id` / `zd_id` / `daili_id` / `sid` / `token` / `name`
- 用站上**未授权的签名接口**签发的 `t`+`sign` 去打弱侧

全部失败也是硬结论:**双实现同源同校验**,不是漏洞。

## 3. 从前端挖兄弟域(最容易漏的一步)

**营销站/官网首页的 `href` 就是组织资产图。** 本轮实测:
```
mall.<主域> 首页外链 → www.<另一独立域> → 对该新域做 DNS 枚举
    ↓
dev.<新域>      ← 开放注册 ⭐
shop.<新域>     ← 商城(订单来源)
www./img.<新域> ← 卖系统源码的站
```
外加同域其它兄弟: `bbs.`(注意: 可能是**伪静态 SEO 引流页**,源码注释常留 `saved from url=(0040)http://.../yazhi/pc/bbs/#`,无用户库,别在上面浪费时间)

**判据**: 子域名解析到 **阿里云/腾讯云裸 IP** = 没有上 CDN/WAF = 不受主站那套封禁策略约束。
解析到 `<x>.bsccdn.com` / `<x>.ctacdn.cn` 之类 = 同一个 CDN/WAF,出货要按老规矩慢。

## 4. 打最弱兄弟站: 开放注册 → 合法会话

- **主站 `/register` 全关 ≠ 组织没有开放注册的站。** 这个结论只在主域成立,换域必须重测。
- 优先顺序: `dev.` > `test.` > `shop.` > `mall.`
- 找注册页: `/index.php/index/user/register`、`/login/register`、`/index/register`、`/users/sign_up`
- **先读表单再提交**: 从 `<(input|form|button)[^>]*>` 抽真实字段名 + hidden 字段 + `__token__`(TP 的 CSRF,一次性)
- 验证码: **ddddocr 优先**,别靠人工看图(见 Pitfalls ⑦)
- 过码后 POST → **判定成功要硬证据**: 用同一会话 GET 一个仅登录可见的页面(如会员中心),看标题是否切换

## 5. 进去之后立刻做的三件事

1. **枚举 oracle**: `check_email_exist` / `check_mobile_exist` 这类未授权校验接口 ——
   双态对照先做**阳性对照**(用你自己刚注册的值),再信它;详见 `captcha-registration-bypass`
2. **上传点 triage**(只花 1 轮判定,别恋战): 见 Pitfalls ⑧
3. **RCE payload 边界**: 见 Pitfalls ⑨

## Pitfalls(全是本轮实测踩出来的)

**① 先读前端真实的 URL 拼法,再 fuzz API 参数 —— 否则全是假阴性。**
本轮我按"单独一个 `list` 参数"打了很久 `api.php`,全是"没有内容"。
读前端才发现真实形态是 **`id=<批次id>,<订单id1>,<订单id2>`(逗号拼在一个参数里)**:
```js
var pUrl = "PrintProtocol://message/?ac="+type+"&sys="+_print_sys+"&id="+bch+list;
//  list = ",订单id1,订单id2..."
```
**参数形状错了 → 结论全废。** 动手 fuzz 之前先把前端的 URL 构造函数读出来。

**② 403 覆盖所有目录时,它不是"目录存在"的 oracle。**
我一度假设 `403=存在 / 404=不存在` 来枚举目录,结果 `inc/ tpl/ sql/ db/ backup/` 全部 403。
**建 oracle 前先跑一个必然不存在的对照组**(`/sql/` `/db/`),对照组也命中 → oracle 无效,整条思路作废。

**③ 免凭据接口需要"服务端生成的 ID"时,这是设计闭环,不是技术差距。**
若未授权接口只吃"调用方已经知道的 ID"(批次号/订单号),而这个 ID 只在登录后才产生 ——
盲扫 ID 无望(SaaS 多租户自增起点很高,扫 100 万次未必命中)。**及时止损,换维度。**

**④ 跳板机解析不了外部域名 ≠ 没有网络。**
现象: `socket.gethostbyname` / `getent` / `curl` 全 000,但目标站能通 —— 说明走的是**代理**(代理侧解析)。
修法: **公共 DNS 按 IP 直连**,绕开坏掉的本地解析器:
```bash
nslookup <name> 223.5.5.5     # 或 dig @8.8.8.8
```
DNS 查询不打目标 WAF,可以放开跑(多线程批查)。

**⑤ 长脚本写文件被截断时,拆成短脚本分步跑。** 宁写 5 个 1200 字符的脚本,不要写 1 个 4000 字符被砍一半的。

**⑥ `pkill -f <脚本名>` 会把启动器自己杀掉。** 启动脚本的 cmdline 里含该名字 → 自杀。
改用 `nohup ... & disown`,或用不会自匹配的 pattern;或"kill / start 分两个 exec"。

**⑦ 验证码是一次性的 —— 读一张就只能提交一次。**
本轮人工读 130x40 的 TP 图形码两次全错(白烧两轮),ddddocr 一次过。
所以**先把 ddddocr 装好再进循环**,不要一边猜一边提交。失败就重取一张(同一会话重取会覆盖旧答案)。

**⑧ 上传点防得好就是死路,一轮判定后立刻撤。**
严实形态 = **扩展名白名单 + `getimagesize` 真图内容校验 + 文件名随机重命名**(文件名被丢弃,路径穿越也没戏)。
本轮 11 种绕过(`.php .php7 .pht .phtm .php3 .php4 .inc .shtml .svg .user.ini .htaccess` + 真图头带 PHP 尾的 polyglot)
分别回 `上传文件格式受限制` / `上传文件不是有效的图片文件`,全部失败。**三者齐备 → 别再耗时间。**

**⑨ ThinkPHP 经典 RCE payload 在较新/已打补丁的站上全 404。**
`?s=index/\think\app/invokefunction&...` 那几个(含 `\think\App`、`\think\Request/input`、`\think\template\driver\file/write`)
本轮 5 组全是 404 —— 404 = 路由没匹配,不是"payload 写错了"。**404 就是这条路封了。**

**⑩ 别解析 flash 提示页来判定成功。**
`温馨提示 / 登录成功 / 页面将在 3 秒后自动跳转` 这类页面里混着内联 CSS,正则容易抓到 CSS 而不是文案。
**判定硬证据 = 用同一会话 GET 一个仅登录可见的页面。**

**⑪ 批量赋值越权要真去看结果,别只看接口回 `code:1`。**
往资料更新接口塞 `is_admin` / `group_id` / `money` / `score`,`{"code":1,"msg":""}` 只表示**请求被接受**,
必须回会员中心**核对余额/积分/权限有没有真的变**。变了才算漏洞。

**⑫ 表单字段名先读再提交,别猜。**
TP 站报 `账户不能为空` = 字段名不是 `username` 而是 `account`。

## 基础设施(跳板机侧)

- **WAF 速率先量,再设计战役。** 本轮实测: 每出口约 **80 次登录 POST** 触发封禁,**封约 40-45 分钟**。
  量出来之后再算总时长,别先启动再看运气。
- **抗封禁守护**: 检测到 403 → `sleep 2700` → 自动续跑 → 命中即写 hits 文件并自停。
- **多出口分工**: 每个出口打字典的一个区间,日志分开写。
- **Python 3.12 系统 pip 被 PEP 668 拦** → 加 `--break-system-packages`,国内机器再挂镜像:
  ```bash
  python3 -m pip install --break-system-packages -q -i https://pypi.tuna.tsinghua.edu.cn/simple ddddocr
  ```
- **凭据纪律**: 会话里出现的跳板机/库/API 口令一律写 `[REDACTED]`,不落盘不入库。

## 反面清单

- ❌ 在同一个域上反复换 payload —— 出口 IP 是消耗品,换维度才有新面
- ❌ 未验证"ID 从哪来"就盲扫 ID 空间
- ❌ 建 oracle 不跑对照组就信它
- ❌ 人工猜验证码(一次性的,猜错就白烧)
- ❌ 把"主域注册全关"当成"组织没有注册入口"
- ❌ 把未跑通的思路写成"已验证方法" —— 未验证的必须明确标注**未验证**

## 相关技能
- 验证码/注册关/枚举 oracle/邮件码: `captcha-registration-bypass`
- SPA JS chunk 提接口: `spa-api-discovery` / `spa-frontend-recon`
- 子域名枚举与接管: `subdomain-enum-takeover`
- 导出/导入型注入: `admin-export-template-sqli`
- 侦察防误判: `recon-discriminators`
- 报告交付: `pentest-report-autogen`

## 实战案例
- `references/jxck-k11-estate-2026-09.md` —— 主目标被 CDN/WAF + 全鉴权封死 → 前端榨出 41 条映射 → 挖出独立域全家桶 → `dev.` 站开放注册 → 注册登录成功 + 枚举 oracle 确认。
