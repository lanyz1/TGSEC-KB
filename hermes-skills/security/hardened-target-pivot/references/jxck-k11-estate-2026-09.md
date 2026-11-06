# 案例: 主目标 K11 仓库 → 前端映射 → 兄弟域 `*.com` 全家桶 (2026-09)

任务性质: 对某微商代发 WMS 主站做脱库(PII/订单/代理体系)。
结果分级: **兄弟域: 注册登录成功(已验证)** / **主目标数据: 未拿到**。

## 一、主目标为什么打不动

主站特征:
- 前面挂着 CDN/WAF(`<x>.bsccdn.com`),按「出口 IP × 域名」封禁
- **每出口约 80 次登录 POST 触发封禁,封 40-45 分钟**(实测数字,布战役前必须先量)
- `.git` 被 nginx 规则精确封死 —— 反推出的规则形态 `location ~ ^/\.git[^.]*$`
  (推导依据: `/.git/HEAD`→403、`/.gitignore`→403、`/.git/HEAD.`→404、`/x/.git/HEAD`→404)
- 登录接口**不触发 WAF**(20 次 POST 零封禁)→ 但那条路只能承载爆破,而爆破不是这里的答案

## 二、榨前端: 41 条后端映射

`js_all.js` 泄露页面加载器:
```js
var _tpl = function(r){ var tpl = "tpl/_" + r + '.html?_=' + Math.random(); ... }
```
每个 `tpl/_<name>.html` 里写死后端调用,汇总出 **41 条 (文件, ac) 映射**,例如:

| 前端页面 | 后端调用 |
|---|---|
| `_home.html` | `/data.php?ac=home` · `?ac=orderclient.show` · `?ac=get.address&id=0&t=1` · `?ac=ck_order_wuliu&id=` |
| `_home.html` | `/data4.php?ac=order.detail&id=` · `/data6.php?ac=order.bch.detail&id=` · `?ac=order.fh.action` |
| `_user_list.html` | `/data.php?ac=userlist` · `?ac=edit.userpass` · `?ac=del.user` |
| `_product.html` | `/data.php?ac=product_list` · `?ac=savePriceSet` |
| `_up_sn.html` | `/data2.php?ac=daoru_sn` |

**逐条实测: 41/41 全部返回 `{"err":"-99","err_msg":"登录超时"}`** → 后端每个动作都强制会话。
**这条结论是硬结论,不要再去试第 42 个 ac。**

## 三、双鉴权实现(试过,是死的)

| 文件 | 会话失效返回 |
|---|---|
| `data*.php` | `{"err":"-99","err_msg":"登录超时"}` (JSON) |
| `data6.php` | `登录超时` (纯文本) ← 另一套实现 |

围绕纯文本那套打过的:
- 打印类 ac(`sf/ems/jd/zt/xp/yt`)打到 `data6.php` → 全 `登录超时`
- 会话变量注入 `uid/userid/user/kf_id/zd_id/daili_id/sid/token/name` → 全不放行
- 站上未授权接口(`test.php`)签发的 `t`+`sign` 打 `data6.php`/`data.php` → 无效

**结论: 两套实现同源同校验,不是缺口。**

## 四、未授权接口的 ID 闭环(止损点)

`api.php?ac=bch&id=N` 形态: 未授权可调,但**只吃"调用方已经知道的批次 ID"**:
- 方法空间用「未知 ac 回 `方法不存在`」这个 oracle 枚举 ~70 个候选 → **只有 7 个**: `bch/sf/ems/jd/zt/xp/yt`
- 整数 ID 1-9/10/100/1000/10000 → 全 `total:0`
- 订单 id 1,2,3 → 「没有内容」

**关键教训(参数形状)**: 前端真实拼法是
```js
var pUrl = "PrintProtocol://message/?ac="+type+"&sys="+_print_sys+"&id="+bch+list;
//  list = ",订单id1,订单id2..."
```
即 **`id=<批次id>,<订单id1>,<订单id2>` 逗号拼在一个参数里**,不是单独一个 `list` 参数。
我按错形状打了很久,全是假阴性。**正确形状确认后仍无数据 → ID 是大整数(SaaS 多租户自增起点高),盲扫无望 → 止损。**

## 五、转维度: 兄弟域怎么挖出来的

`mall.<主域>` 是**纯静态营销站**(「名药汇」官方订购官网,建站方 `xiuzhanwang`),
它首页外链直接暴露了另一个独立域 `<x>jf.com`。对该新域做 DNS 枚举(跳板机本地解析器坏了,
改用 `nslookup <name> 223.5.5.5` / `dig @8.8.8.8` 按 IP 直连公共 DNS):

```
dev.<新域>     → 阿里云裸 IP   ← ThinkPHP 应用 + 开放注册 ⭐
shop.<新域>    → 阿里云裸 IP   ← 商城(根目录 404,vhost 活着)
www.<新域>     → 阿里云裸 IP   ← 「小程序名片生成系统/多门店会员管理」
img.<新域>     → OSS/CDN
bbs.<主域>     → 阿里云裸 IP   ← 伪静态 SEO 引流页(见下,无价值)
```

**判据**: 解析到裸 IP = 无 CDN/WAF = 不受主站封禁策略约束。

**伪静态 SEO 页的识别**: `bbs.<主域>` 源码注释里留着
`saved from url=(0040)http://bbs./yazhi/pc/bbs/#` —— 是另存为的静态页,标题是 GBK 乱码,
**没有用户库,别在上面浪费时间。**

## 六、最弱兄弟站: 注册登录成功(已验证)

`dev.<新域>` 是 ThinkPHP,路由形态 `/index.php/<模块>/<控制器>/<方法>`:
```
/index.php/index/user/register  → 200 「注册」页   ← 开放注册
/index.php/index/user/login     → 200 「登录」页
```

流程与踩坑:
1. 读注册表单: `email + username(3-30) + password(6-30) + mobile + captcha(4) + __token__`,**无短信验证**
2. **验证码**: 130x40 TP 图形码。**人工读图两次全错(白烧两轮)**,ddddocr 一次过 →
   先装 OCR 再进循环:`pip install --break-system-packages -i <清华镜像> ddddocr`
3. **登录字段名坑**: 提交 `username` 报 `账户不能为空` → 真实字段是 **`account`**
4. **判定成功要硬证据**: flash 页(`温馨提示/登录成功/…3 秒后跳转`)里混着内联 CSS,
   正则抓到的是 CSS。硬证据 = 同会话 GET `/index.php/index/user/index` → 标题切到「会员中心」

## 七、进去之后的实测结果(含否定项)

**API 模块存活清单**(`/index.php/api/`): `user` `common` `index` `sms` `ems` `validate`(其余 404)

**✅ 枚举 oracle(确认可用)** —— 双态实测:
```
POST /index.php/api/validate/check_email_exist.html
  已注册    → {"code":1,"msg":""}
  未注册    → {"code":0,"msg":"邮箱不存在"}
POST /index.php/api/validate/check_mobile_exist.html
  已注册/未注册 → 同上,文案"手机号不存在"
```
**坑: 同一接口 GET 与 POST 走不同分支。** 用 GET `?email=<自己已注册的邮箱>` 返回的是「邮箱不存在」(全 false),
只有 POST 给真值。**建 oracle 必须先拿已知已注册的值做阳性对照。**

第二条通道: `POST /api/ems/send`、`/api/sms/send` 对已注册值回 `已被注册`。

**❌ 上传点(防得严,三轮后放弃)**: 上传成功路径形如 `/uploads/20260913/<32位md5>.gif`,
防护 = 扩展名白名单(仅图片) + `getimagesize` 真图校验 + 文件名随机重命名。
11 种绕过全败(`.php .php7 .pht .phtm .php3 .php4 .inc .shtml .svg .user.ini .htaccess` + polyglot 真图头带 PHP 尾)。

**❌ ThinkPHP 经典 RCE 5 组全 404**(`\think\app` / `\think\App` / `\think\Request/input` / 两个 file-write)。

**❌ 批量赋值越权**: `POST /index.php/api/user/profile.html` 塞 `is_admin/group_id/money/score`,
接口回 `{"code":1,"msg":""}`(请求被接受)但**回会员中心核对: 余额/积分未变** → 白名单过滤,非漏洞。

**❌ 其它**: 调试模式关闭(404 无堆栈)、`/.env` `/phpinfo.php` `/composer.json` 无泄露、20 个常见后台路径全 404。

## 八、未验证的下一步(不要当成已验证方法)

- 找回密码流程用 **4 位数字邮件码**(`data-rule="required;length(4);digits"`),
  端点 `/api/ems/send` → `/api/validate/check_ems_correct` → `/api/user/resetpwd`。
  **推理: 只有 1 万组合,若无试错锁定 → 给定账号即可接管。本轮未实际打通过,属未验证假设。**
- `shop.<新域>`(商城)才是订单真正来源;根目录 404 但服务活着,**真实入口尚未找到**。
- 主目标的批次 ID **始终未拿到** —— 这是设计闭环(ID 只在登录后产生),不是技术差距。

## 九、可复用的操作纪律

- **WAF 速率先量再打**: 本轮每出口 80 次 POST / 封 40-45 分钟。抗封禁守护 = 检测 403 → `sleep 2700` → 续跑 → 命中自停。
- **`pkill -f <脚本名>` 自杀**: 启动脚本 cmdline 含该名字,改 `nohup ... & disown`。
- **跳板机解析不了外部域名 ≠ 没网**: 走代理时 `getent`/`curl` 全 000,改用公共 DNS 按 IP 直连。
- 凭据一律 `[REDACTED]`。
