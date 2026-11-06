---
name: crypto-web-campaign-patterns
description: "Use when Anshin MT5/OKX ACE/faka/epusdt MiniApp."
version: 1.2.0
tags: [anshin, mt5, okx-affiliate, usdt, approve, fixed-address, seo-funnel, jbridgek, dujiaoka, epusdt, faka, tron-energy, miniapp, dicevault, web3-relay]
---

# Crypto / Web 战役模式（2026-09 沉淀）

授权红队多目标时的**类级**识别与攻击链：MT5 门户、OKX 拉新 SEO 壳、独角/小柒发卡+epusdt、TRON 能量 Mini App、USDT 固定收款 vs 授权盗 U。

Related（只读/交叉，未必可改）：`pentest-execution` · `defi-authorize-drain` · `caishen-heyue-authorize-faka` · `cdn-origin-tracing` · `reverse-skill`。

## When to load

- Anshin / portal.anshinfx / MT5 客户登录 / `apiSecret` + RSA 密码
- 假交易所/钱包下载 / `ACE53` channel / `mxkdpwvhqrn` / `btmzhjpdgxc` / `cbjollery.mpwrs.cn`
- 用户问「是不是授权盗 U」/ 固定地址收款号商站 — **先对照表定性再深挖**
- 质押/挖矿/理财盘 + 真代币 + 真合约（自写 Staking/Treasury/Payout 三件套，例 Venice VVV 假质押盘）
- 小红书号批发 + USDT 多链收款 + 混淆 JS（jbridgek 类）
- 独角数卡 / unicorn 主题 / `dujiaoka_locale` / 小柒.APP / epusdt `:8000` / `pay.*` 子域
- TRON 能量租用 / freeEnergyBot / `api.*/api/session/init` + Telegram WebApp
- DiceVault / Provably Fair Dice / Windows Node relay `:3000` / `ethers` + Sepolia 标题

## 先分类（CRITICAL）

用户口头禅「这个是授权盗U吗」→ **先回对照表**（1 屏），再继续打，禁止闷头扫完才定性。

| 形态 | 信号 | 硬资产 | 下一刀 |
|------|------|--------|--------|
| **授权盗 U / heyue** | approve MAX、`/payment-config`、spender | owner/spender 钥 | defi/caishen；无钥 `BLOCKED_NO_KEY` |
| **固定地址收款** | 二维码/复制地址、无 approve | 收款 EOA 钥（常无） | 抠地址链上溯源；入口常静态 |
| **发卡 faka（独角/小柒）** | `/buy/{id}`、`create-order`、bill、易支付/epusdt | 卡密库存+支付密钥+admin | `references/dujiaoka-epusdt-faka.md` |
| **TRON 能量 MiniApp** | 能量租用壳、`initData`、无钱包 approve | 收款/充值热钱包+bot | `references/tron-energy-miniapp.md`；API 522 先兄弟域/等源站 |
| **Anshin MT5 门户** | Next `/api`→gateway、apiSecret | MT5 明文密码+改密 | `references/anshin-mt5-portal-attack-chain.md` |
| **OKX ACE53 SEO 壳 / EdgeOne 镜像农场** | 静态落地→atob→join/APK；或 EdgeOne 镜像真 OKX UI（`/api/v5` 活、登录同 3901） | 渠道/真链导航后台/运营面 | `references/okx-affiliate-seo-funnel.md`；**镜像无独立业务后端**→改打真链 OneNav/WP |
| **Web3 Dice/Relay（DiceVault 类）** | Sepolia 标题、`/api/auto-bet`、`ethers` CDN、Windows `C:\…\frontend` | 主机 `.env` PRIVATE_KEY（常=合约 owner） | `references/web3-relay-dice-windows-lfi.md`；**先定性测网 vs 主网** |
| **真质押盘 / 存款即变现庞氏** | 链上 `stake()`→Treasury→swap→`projectWallet`；`approve` 给的是**业务合约**而非恶意 EOA；业务合约 token 余额=0 | 用户本金（已被变现成 native 进运营方 EOA） | `references/staking-ponzi-vs-approve-drain.md`；**先判档再打** |
| **白标博彩 H5（开云/apeiro8 类）** | 主域只是**下载落地页**（零 input）；真 H5 在 `*/entry/register`、`*/mine/*`；`X-API-SITE:4002`；报错页出现 `apeiro8` | 真玩家/代理账号（免鉴权注册即得）、免鉴权接口 | `references/white-label-gambling-h5.md` |

详细对照：`references/usdt-fixed-address-vs-approve.md`。

## Anshin MT5（摘要）

1. `GET /api/app/apiSecret` 未授权 → `api-secret-key` + RSA 公钥
2. 密码：`js-base64 encodeURI`（**不是** `encodeURI()`）→ RSA PKCS1 → 提交
3. 枚举：`USER_01_01` 不存在 / `USER_01_08` 存在
4. 注册：`action=register` 发码 → register 体拿 JWT
5. **Critical** `GET .../mt5/info?account=` 明文密码；`POST .../update/tradePassword` 可改
6. 多 IP 同库（121.40 / 39.106）；无助记词/链上私钥

全文：`references/anshin-mt5-portal-attack-chain.md`。

## OKX 拉新漏斗（摘要）

落地静态 → `reg.oereg|ouyir` 或 `url/okx.html` → EdgeOne 跳板atob reverse → `btmzhjpdgxc.org/join?channelId=ACE53…` + `cbjollery.mpwrs.cn/.../android_ACE….apk`（~450MB 真 OKX 壳常见）。

**镜像农场变体（k0.usdtrlc 类）**：落地→跳板→`/api/v5` 活且行情≈真 OKX；登录 `needPublicKeyHeader`/`needJwtSign` 与 www.okx.com 同 3901 → **无独立 admin**。改打：（1）落地/`sites/*.html` **真连**导航站（OneNav/WP 开放注册→`/user/`）；（2）裸 nginx 易欧 SEO 集群（`/admin` 域名授权门）；（3）OSS/mpwrs 下载面。**关联闸**：只认 A 记录同 IP 或首页/JS 真连；FAQ/友情链/第三方 IM/无同 IP 的 admin 不升权。

全文：`references/okx-affiliate-seo-funnel.md`。

## 固定地址号商站（摘要）

GitHub Pages 静态；购买弹窗；配置在 zlib+`eNr` base64；解压抠 EVM/TRX/SOL。无 payment-config、无 approve。

## 独角 / 小柒发卡 + epusdt（摘要）

- 指纹：`dujiaoka_locale` / unicorn CSS / `Powered by` / robots 泄 `manage-<hex>`
- 小柒 V14：`/manage-<16hex>/auth/login` 可无验证码；**不能**直接套老独角≤2.0.4 merchant_id=key 伪造
- 经典独角：`POST /create-order` → `/bill/{SN}`；查单有的只要 SN（无查询密码）= 隐私/枚举面
- epusdt：`pay.` 子域或 `:8000` 回 `hello epusdt`；API 要 `api_token` 签名；收银台页 `data-clipboard-text` 直接吐 **TRC20 收款地址+金额**
- 支付跳转抓 pid/key 后再签 yipay/epusdt notify；弱 token 字典常失败勿空耗

全文：`references/dujiaoka-epusdt-faka.md`。

## TRON 能量 MiniApp（摘要）

- 壳标题「能量租用」；`APP_VERSION` + `freeEnergyBot.miniappToken`；API 默认 `https://api.<root>/api`
- 鉴权：TG `initData` → `POST /session/init` → Bearer；浏览器无 TG 会直接抛「请在移动端 Telegram 访问」
- 未授权优先：`GET /config` `/swap`（packages、paymentAddress、depositAddress、customerServiceTg）
- **不是** approve：转账 TRX/USDT 到后台配置地址；风控文案「活跃度不足/请用转账租用」
- CF **522** = 源站挂：前端仍可 RE；落盘 API map；扫 `bx/m/gx/pao/tron/xm` 兄弟壳；等 API 活了再打 session/IDOR

全文：`references/tron-energy-miniapp.md`。

## Web3 Dice / Relay（摘要）

Windows Node 自写静态服 + 链上 dice/relay 常见：
1. `/server.js` `/config.js` `/package.json` 直接 200（源码面）
2. 静态 `baseDir + pathname` **无规范化** → `/..\/.env` 读上级 `.env`
3. Hardhat 默认钥 `0xac0974be…f2ff80` 常硬编码在 fallback；**真钥在 `.env` 的 `PRIVATE_KEY=`**
4. 未授权 `/api/admin-safe-reset` `/api/reveal-seed` `/api/admin-fix-max-sessions`
5. 拿钥后：**先主网余额定性**；用户说「测试的不要」= 停测网庆祝、继续抠第二把主网钥 / 全链 USDT

全文：`references/web3-relay-dice-windows-lfi.md`。

## 真质押盘 / 存款即变现庞氏（摘要）

**触发**：用户问「这个是授权盗U的站吗」，而目标有真代币 + 真合约 + 质押/挖矿/理财功能。
**别二元回答** —— 分三档：①真 approve-drainer ②假盘但用户自愿存入（本类）③合法被误判。只有 ③ 才停手删档。

1. **读合约头注释**：常自己写明流向（`STAKE: user TOKEN ──transferFrom──▶ Treasury ──swap──▶ ETH ──▶ projectWallet`）。比读代码快。
2. **`grep transferFrom <Staking>.sol`**：全合约仅 1 处且在 `stake()` 内 ⇒ **不是 drainer**。
3. **托管检查**：staking 的 token 余额 = 0 ⇒ 本金不留合约（存款即变现信号）。
4. **追变现**：`alchemy_getAssetTransfers` 累加 Treasury 卖出的 TOKEN + projectWallet 收到的 native。
5. **存续判据**：Blockscout v1 `?module=logs&action=getLogs&topic0=…` 数 `PrincipalWithdrawn` / `RewardClaimed`。
   >0 = **仍在兑付，不是已跑路**（口径要写清，别当跑路盘报）。
6. **价格口径**：合约 `getLatestPrice()`（自有预言机，常虚高 2x）vs 路由 `getAmountsOut` / 真实市价。
   汇报**必须两栏**：平台口径 vs 真实口径。
7. **兑付缺口**：payout 合约 native 余额 vs 账面质押总额；payout 资金若来自运营方 EOA 而非营收 = 靠回填撑着的盘。

一条命令跑完 1/3/4/5/6：`python3 scripts/evm_money_trail.py --staking <S> --vvv <T> --rpc <alchemy> --chain base`

全文 + API 细节 + 结论口径模板：`references/staking-ponzi-vs-approve-drain.md`。

## 铁律

- 「继续」= 换面深挖，禁止「已到极限」
- 「是授权盗U吗」→ 先分类表，再深挖；**分三档**：①真 drainer ②假盘但用户自愿存入（存款即变现庞氏）③合法被误判 —— **只有 ③ 停手+全删**；非盗U ≠ 合法生意
- 判 drainer 的硬判据是**资金流向**，不是 `approve` 是否存在（业务合约收 MAX 授权是常规做法）
- 无 spender/owner 钥禁止假装链上抽币
- **「测试的不要 / 只要主网」** → 立刻停测网归集叙事；继续 LFI/备份目录/PS 历史找第二把钥；主网扫全链 native+USDT/USDC/主流 ERC20（Ethplorer 补漏）
- Hardhat#0 ≠ 生产钥；`.env` 与源码 fallback 必须分开验地址与链
- 静态 SEO 壳 3 次确认无 API 后：报告漏斗节点，APK/FOFA 或换目标——勿空耗 path 字典
- 同前端 hash + 跨 IP 邮箱 EXISTS = **同用户库**，凭证/枚举结果可复用
- 切换目标：旧目标 `/tmp/<name>/REPORT.md` 或 `cases/<ip>/notes/REPORT.md` 落盘再 mkdir 新目录
- epusdt/yipay 端点存在 ≠ 可伪造；先抓真实商户参数
- **判据纪律（CRITICAL）**：测「客户端身份头是否被信任」必须用**不存在的账号**做对照（存在/不存在/全0/全f 四组）。行为一致 ⇒ 该头未生效，**立即作废结论**。反面教材：`X-USER-ENCY = md5(用户名)` 看着像万能身份牌，回包差异实为**重复请求频控**（6011 `请勿重复操作`），差点误报「账号状态 oracle」；自账号为空时「返回空」既可能是隔离也可能是对方本无数据 ⇒ **不可区分就不下结论**
- **封禁按域独立**：同一后端多域名，某域被 WAF 封（HTTP 416 安全阻断 / 浏览器 `chrome-error://`）**不等于全站封**，也**不等于要上浏览器** —— 换另一域名继续用 curl（会话 token 跨域通用）；域名矩阵从**免签** config/`localStorage` 拿
- **密钥按域**：AES k/v **每个域各一套**，跨域复用会 `Incorrect IV length` / 解密乱码；换域先重取一次免签密钥接口
- **写面别空耗**：自由文本/上传 → 自家 CDN 存储型 XSS，本类平台普遍备了四层（类型白名单+魔数校验+WAF+回包正确 Content-Type）。字段名用**空 body 探针**（服务端错误文案直接告诉你缺什么）、**长度门槛**（如「描述 20~200 字」）比穷举字段名快得多

## References

- `references/anshin-mt5-portal-attack-chain.md`
- `references/okx-affiliate-seo-funnel.md`
- `references/usdt-fixed-address-vs-approve.md`
- `references/dujiaoka-epusdt-faka.md`
- `references/tron-energy-miniapp.md`
- `references/web3-relay-dice-windows-lfi.md`
- `references/staking-ponzi-vs-approve-drain.md` — 真质押盘 vs 授权盗U 三档定性 + 链上取证 API（Alchemy `getAssetTransfers`；Alchemy 全量 `eth_getLogs` 被拒时改 Blockscout v1 `getLogs`）
- `scripts/evm_money_trail.py` — 一条命令跑完托管检查 / 变现流水 / 兑付存续 / 价格口径（只读）
- `references/white-label-gambling-h5.md` — 白标博彩 H5（apeiro8 系）玩家/代理端：模块签名常量、免鉴权接口矩阵、反馈/上传 schema 与四层防御、越权接管边界、判据纪律与换域续攻
