---
name: php-vendor-shell-family-attack
description: "Use when 审计厂商独立 PHP 壳脚本族(中转/收银/代付)。"
version: 1.0.0
tags: [php, source-audit, ssrf, aes, vendor-family, 中转, 收银]
---

# 厂商独立 PHP 壳脚本族（中转/收银/代付/回调）

适用：拿到某个灰产/支付厂商分发给多家品牌的**一组互不依赖的独立 PHP 文件**（不是框架工程，就是 `xxx.php` 平铺在 webroot）。这类文件族一套源码卖多品牌，**一份拷贝 = 全套文件名 + 内网地址 + 密钥位置**，是横向打整个家族最高效的杠杆。

配套：平台本身（凤凰系统/FHSYS、iredcap 中通族）的业务面、登录面、出金面见 `pentest-execution` 的 `references/platform-attack-chains.md`。本技能只管**这批壳脚本怎么读、怎么用**。

## 0. 先建文件名字典 + 找活实例

壳脚本族的文件名本身就是指纹，**拿一份源码就能去对打同族所有实例**（分发时文件名不变）：

```
index.php pay.php tools.php tools2.php AppletProducts.php
CnyNumber*.php JDECard.php QQFaceRed.php QianxinTransfer.php
payCardPwd.php uid.php uidtransfer.php uploadMoneyImg.php
recordVisistInfo.php orderQuery.php updateOrderPayUsername.php
updateOrderPayUsernameNoLockCode.php alipay*.php wechat*.php
wechatGroupRed.php taoBao*.php douyinGroupRed.php zz.php fileadmin/
```

扫描要点：
- **用长尾文件名当探针**（`AppletProducts.php`、`updateOrderPayUsernameNoLockCode.php` 这种不会有误报），逐个文件 GET/POST 两法都试——**这类壳多为 POST 语义、GET 可能被 nginx 拒**。
- **结果码走读**：`200 + HTML 片段`= 壳活着；`404`= 没部署；**统一 `403`（且页体明显变大，例如从 ~146B 涨到 ~548B）= WAF/限流层挡了，不是文件不存在** ⇒ 换出口 IP 再打，别据此判定入口消失。
- 一套文件常同时部署在**公开实例**和**内网机**上；内网那批才是你要借道打的目标（见 §4）。

## 1. 硬编码密钥与内网拓扑（一次 grep 拿全）

```bash
grep -rnE "define\\( *'" --include='*.php' .          # 内网 base URL + 加密密钥全在这里
grep -rnE 'AES|SECRET|KEY|IV|encrypt|decrypt' --include='*.php' .
```

`tools.php` / `tools2.php` 是壳脚本族的**公共库**（加密、签名、`httpRequest` 转发），**壳文件名可以变，`define` 常量不会变** —— 所以这两个文件优先读。里面通常直接写着：
- 两组 `AES-128-CBC` 的 key/IV（旧钥 + 新钥，`decrypt` 失败回退新钥）；
- 内网壳机的 base URL（中转机、上传机、下单接口）；
- 内层转发密钥（`$inner_transfer_secret` 之类，用于 `getSign`）。

**密钥值不要抄进报告/技能**（用户铁律：密钥 [REDACTED]）；记住**位置**即可（`tools.php` 头部 define 行），有源码就能现取。

已知一族（iredcap 中通/亚虎支付中转族）的内网地图：中转 `43.225.47.56:88`（updateOrderPayUsername / payCardPwd / uploadMoneyImg / orderQuery / recordVisistInfo）+ 上传 `45.207.36.23/upload.php`。

## 2. 还原加密（本机复现，先跑自检）

1. 从源码读准：算法（这类基本是 `AES-128-CBC`）、key/IV（字符串直接当 raw key，不是 hex 解码）、padding、外层编码（`base64`）。
2. 本机用 `pycryptodome` 复现 `encrypt()/decrypt()`，**必须先自检 `dec(enc(x)) == x`** 再用它造任何参数——不自检就发包，会浪费一整轮在"参数解密后是空串"上。
3. 自检通过 ⇒ 壳脚本里**任何被 `decrypt()` 的参数都是你可控的**（`key` / `qr_img` / `gourl` / `host` 类字段）。

## 3. 空 guard：验签/鉴权"写了但没生效"（先扫这个，比找后门快）

```bash
grep -rnE 'if *\\(.*(!==|!=|==).*\\).*\\{ *\\}' --include='*.php' .
```

典型形状（实测存在于本族收银壳）：签名**算出来了**却丢进**空 guard 体** ——

```php
$sign = getSign(array_merge($_GET, ['key' => $inner_transfer_secret]));
if ($sign !== $_GET['sign']) { }        // 判断结果被丢弃 = 未授权直通
```

同一族还有把 `die("签名错误")` 注释掉的变体。**判定为未授权直通后，用一条真实请求验证**（拿到业务响应 vs 被拦），别只凭代码下结论。

## 4. `decrypt(参数)` 当主机 = 任意主机 SSRF（内网唯一入口）

本族壳脚本的招牌写法：

```php
$ret = httpRequest('http://'.decrypt($_POST['key']).'/api/pay/updateOrderPayUsername', 'post', $data);
```

- **`decrypt()` 后的值直接成为请求主机** ⇒ 有密钥（§2）就能指向任意主机/端口 ⇒ 打**外网直连不到的内网壳机**。
- **内网主机 ConnectTimeout 不是"下线"**：那是设计如此。外网直连超时 ⇒ 唯一入口就是公开实例上的这层 SSRF，不要因为超时就判这条线死了。
- 同族同构壳：`recordVisistInfo.php`、`orderQuery.php`、`payCardPwd.php`、`uploadMoneyImg.php`、`updateOrderPayUsername.php`。
- **业务价值最高的两个是收款人/订单变更类壳**：`updateOrderPayUsername.php` 与 `updateOrderPayUsernameNoLockCode.php`（后者免锁码校验）；调用链是 `公开实例壳 → SSRF → 内网中转壳 → 业务接口`。
- ⚠️ **未端到端验证**：本条已验证的是源码事实（`decrypt` 当 host）与内网主机外网不可达；`公开壳→SSRF→内网壳→业务写入`整链**尚未跑通**。下一步的正确做法是**先在 SSRF 上加回显/回读**（壳的 `print_r($ret)` 就是回显通道，用它读内网壳的返回），确认转发到达后再动业务写接口。

## 5. 验证纪律（壳的"成功"不算成功）

- 壳脚本回显的是**它自己 curl 到的东西**（`print_r($ret)`）⇒ 壳返回 200 只证明转发发生，**不证明业务接口接受**。必须再打平台自己的**读接口**核对（订单/配置/余额），两端一致才算生效。
- 厂商源码 dump / 演示库里的口令**不是战果**：那是厂商演示数据，运营上线必改，只当枚举字典用。
- 任何"已改/已成功"的话都要有落库回执或读回证据；提交 ≠ 生效 ≠ 到账。

## 6. 常见坑

- **壳是平铺的独立文件，不是框架路由**：不要拿框架那套（`?s=`、PATH_INFO、控制器 fuzz）去套，直接按文件名打。
- **403 页体大小是判据**：同一路径前后页体大小不同（146B vs 548B）说明拦截层换了，不是路由变了。
- **`fileadmin/`、`upload.php` 这类文件管理/上传壳随仓库分发**，是拿 webshell 的现成入口，优先测（注意可能有独立 IP 白名单）。
- **一套源码多品牌 ⇒ 账号体系不通用**：壳脚本和密钥通用，但后台/码商/商户的票不通用，别把一处的会话拿到另一处用。
- **代理池打内网壳无效**：内网地址从公网任何出口都不可达，只能走 SSRF。
