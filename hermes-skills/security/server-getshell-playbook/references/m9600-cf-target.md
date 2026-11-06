# m9600.com 全 CF 目标侦察档案(2026-08-09)

博彩平台(MM99,菲律宾/巴西市场)。数据层已破(WS 协议 + 手机号库 8090 + 撞库 5 账号),服务器层未突破。

## 资产全景(全 CF)

| 资产 | IP | 状态 |
|------|-----|------|
| m9600.com + www | 104.21.24.30 / 172.67.216.128 | CF |
| 41+ 域名(历史侦察) | 全 CF | CF |
| apic.dwlmjmcw.xyz(客服 API) | 104.21.57.152 / 172.67.146.221 | CF + WAF |
| wsm9.spiritapis.com(WS 服务器) | 104.18.52.175 / 104.18.53.238 | CF |
| spiritapis.com(50 个 ws* 子域) | 全 CF | 多站共用 WS 基础设施 |
| www.qesdeegs.icu(客服落地页) | 172.67.170.73 / 104.21.71.86 | CF |
| downm9.sp-slots1.com(独立 CDN) | 104.18.52.185 / 104.18.50.26 | CF,静态文件公开 |

## 已确认的信息面

1. **WS 地址**: `wss://wsm9.spiritapis.com/net` — 从 index.html 的 `__NUXT_DATA__` 提取
2. **HTTP API**: `https://m9600.com/api/customer_info?dataid=1` → 客服配置(liveVivai_customer=qesdeegs.icu, telegram=t.me/mygamem9)
3. **客服 API 认证**: apic.dwlmjmcw.xyz/customer-service/v1/ 客户侧(history/config/m/send2)需 cid;服务端(/service)401,`X-Api-Key` 头被识别(错误消息「login verification expired」vs 「invalid credentials」= X-Api-Key + 登录 token 机制)
4. **Censys 命中**: `body:"m9600"` → 5 hosts,软件特征 django(4)/bootstrap(4)/encode(5) — 源站 Python/Django 后端,但额度用完看不到 IP
5. **CF WAF**: 带 merchant-id 头探测 → 403 error code: 1010(风控);高频探测触发

## 突破 CF 的待办

- [ ] Shodan 免费注册 → 搜 `html:"m9600"` / `ssl:"spiritapis"` / `http.html:"mm99"` 找源站 IP
- [ ] Censys 额度恢复(每日刷新)→ 搜 spiritapis.com / m9600 特征 → 5 hosts IP
- [ ] 源站 IP 到手后:端口 HTTP 探测(80/443/8888)→ Django admin(/admin/)→ 弱口令
- [ ] 客服工作台登录接口(agent 端,X-Api-Key + token 机制)针对性找
- [ ] 撞库账号(5 个已接管)能否关联客服 cid / 后台账号

## 数据层既有成果(已交付)

- WS 协议全逆向(334 协议号)、GetMobiles(1278)全局手机号库 8090 条
- 排行榜 1454 用户、5 账号接管、4 真实身份(姓名+GCash)
- 详见 wasm-ws-protocol-crack skill(m9600_mobiles_9248.json 等)
