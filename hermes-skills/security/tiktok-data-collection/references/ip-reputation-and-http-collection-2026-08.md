# IP 信誉判定 + 纯 HTTP 采集（2026-08-17 实测证据链）

背景：用户连续报"应用了 wukong 协议仍采不到 CK 登录账号的作品"，且反问"我那会给你的 SK5 IP 不是住宅 IP 吗"。五轮实测后结论反转——**IP 干净，真凶是 Chrome 自动化被 JS 反爬降级**。

## 证据链（按顺序）

| # | 测试 | 结果 | 结论 |
|---|---|---|---|
| 1 | tokenBeat 官方验证（wukong Cookie + SK5 代理） | ok:true | 登录态有效 |
| 2 | CDP 采集 @fan87921（登录账号） | SSR postData 空（json_200_） | 疑似风控 |
| 3 | CDP 采集 @tiktok（对照组，verified 账号） | 同样空 | **不是账号问题** |
| 4 | 签名器诊断：webmssdk scripts=2 global=true、fetch 被 hook、滚动 DOMvids:0 | 签名器正常但无数据 | 排除签名器/时序 |
| 5 | 香港服务器直连 curl @tiktok | **12KB 骨架页 + captcha** | 香港机房 IP 被降级 |
| 6 | ip-api.com 查 199.239.16.12 | **hosting:false proxy:false**（NTT America, Centennial CO） | **用户代理 IP 非机房** |
| 7 | 用户代理 curl @tiktok（服务器上走 socks5-hostname） | **368KB + videoCount:1491 + itemList** | **IP 干净，纯 HTTP 拿全数据** |
| 8 | 同 IP：游客 Chrome（无 cookie）@tiktok | title 变 "TikTok - Make Your Day"（**跳首页**）+ items:0 | Chrome JS 反爬跳转 |
| 9 | 反自动化补丁（--disable-blink-features + navigator.webdriver 覆盖）后重测 | **仍失败**（SSR 空） | **补丁不够，别死磕** |

## 关键判别命令

```bash
# 1) IP 类型权威检测（通过代理本身查）
curl --socks5-hostname 'USER:PASS@HOST:PORT' \
  'http://ip-api.com/json/?fields=query,isp,org,as,proxy,hosting,country,city'

# 2) IP 是否被 TikTok 降级（铁律：先用这个，别直接怪 IP）
curl -s --max-time 30 --socks5-hostname 'USER:PASS@HOST:PORT' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36' \
  -o /tmp/tk.html 'https://www.tiktok.com/@tiktok'
wc -c /tmp/tk.html                        # ≥200KB = IP 干净；<15KB = 降级
grep -oE '"videoCount":[0-9]+' /tmp/tk.html   # 有值 = 数据在
grep -cE 'captcha|verify' /tmp/tk.html    # 骨架页特征
```

## Chrome JS 反爬判别法

页面 evaluate 时查 `document.title` / `location.href`：
- title = "TikTok - Make Your Day" 且 href 非 @handle = **被 JS 跳首页**（反爬，与 IP/签名/时序无关）
- 反自动化补丁（AutomationControlled + webdriver 覆盖 + chrome.runtime 隐藏）**实测无效**
- 不要再投入浏览器反爬对抗——绕开浏览器

## im/user/profile 兜底（附）

`GET https://www.tiktok.com/tiktok/v1/im/user/profile/?aid=1988&user_ids=%5B<uid>%5D`
- user_ids = **URL 编码 JSON 数组**（`%5Buid%5D`），裸 uid → Invalid parameters
- 带 Cookie + UA + sec-ch-ua + Origin/Referer → status_code 0 + `users[0].im_user_profile`
- 免签名，数据中心 IP 也能用；uid 从 `multi_sids=(\d+)` 取（uid_tt 会被脱敏截断）
