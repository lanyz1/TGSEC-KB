# 斗篷风控引擎 + Meta Pixel CAPI 回传(实战实现)

来源: 马总COD(xeelee.top)生产部署实战, 2026-08。PHP 8.2 + SQLite, 零外部依赖(纯服务端检测 + SVG/原生 JS)。

## 一、斗篷(Cloak)11 规则引擎

### 配置模型
- 存 `dr_settings(k='cloak_config', v=JSON)`, 默认值数组 `cloak_defaults()`: enabled/huiliu_url/auto_black/country+country_list/zh_hit/vpn/idc/fb_cidr/repeat+repeat_window+repeat_times/os+os_list/model+model_list/platform+platform_mode(block|allow)+platform_list
- 保存: `INSERT OR REPLACE`(见 SKILL.md SQLite 3.7 坑)

### 检测信号源
1. **IP 情报(国家/VPN/机房)**: `http://ip-api.com/json/{ip}?fields=status,countryCode,isp,org,proxy,hosting,query`
   - **proxy/hosting 布尔字段直出** = VPN检测+机房拦截的核心信号, 免费 45 req/min
   - 必须 DB 缓存(`dr_ip_cache`, 24h TTL, INSERT OR REPLACE), 否则流量大直接限速
   - 本机/内网 IP(127.0.0.1/192.168.x/10.x)直接返回空情报跳过(开发环境不误伤)
   - 兜底关键词: VPN|proxy|tor|shadowsocks|socks; IDC: hosting|cloud|datacenter|aliyun|tencent|digitalocean|vultr|hetzner|ovh|azure...
2. **UA 解析**: `cloak_parse_ua()` → os(windows/android/ios/macos/linux)/platform/model(iphone/品牌机型正则)
3. **Accept-Language**: 中文命中 = `preg_match('/zh|zh-cn|zh-tw/i', $lang)` 或 UA 含 zh
4. **Facebook CIDR**: 内置 16 个网段(AS32934): 31.13.24.0/21, 31.13.64.0/18, 66.220.144.0/20, 69.63.176.0/20, 69.171.224.0/19, 69.171.248.0/21, 102.132.96.0/20, 129.134.0.0/17, 157.240.0.0/16, 163.114.128.0/20, 173.252.64.0/19, 179.60.192.0/22, 185.60.216.0/22, 204.15.20.0/22, 31.13.96.0/19, 45.64.40.0/22; cidr_match 用 ip2long + mask(仅 IPv4)
5. **指纹**: URL 参数或 cookie 里的 40-64 hex; 否则 md5(ip+ua)
6. **重复访问**: `dr_cloak_visit` 表记录 (ip,fp,inputtime), 窗口内 COUNT >= 阈值即拦; 定期清理 2h 前数据

### 执行顺序(cloak_check → cloak_apply)
1. 总开关 enabled=0 → 直接放行
2. blacklist 命中 → hits[]('blacklist')
3. **管理员放行(HMAC 签名 cookie)命中 → return []**(必须优先于其他规则, 否则被误拉黑的管理员也进不来)
4. 国家/中文/VPN/机房/FB CIDR/重复/系统/型号/平台 依次检测
5. cloak_apply: 写 `dr_cloak_log`(ip,fp,ua,lang,rule) + auto_black 时写 `dr_blacklist`(expire=7天) → 返回 true

### 管理员放行(防伪造)
- `cloak_back_ok()`: cookie `cacod_back = 1.<hmac>`, key=`hash('sha256', cfg('admin_pass').'::cacod_back')`, hmac=`hash_hmac('sha256','1',$key)`; hash_equals 校验
- 后台登录成功(index_login)种 30 天; logout 清除
- **不要用明文 cookie/URL 参数放行**(同行一眼伪造绕过全部规则)

### Hook 点
- 商品页: `pro_show()` 开头 `cloak_page_guard('/')`(命中输出 `<script>window.location.replace(url)</script>` 回流页 + exit)
- 下单: `order_buy()` 开头 cloak_check(false) + cloak_apply → json_out(0,'下单失败, 请稍后再试')(不暴露原因)

### 测试方法(生产验证)
1. 开 zh_hit → `curl -H 'Accept-Language: zh-CN' URL` 应得回流页 HTML(200 + <title>页面加载中</title>)
2. 伪造放行: `-H 'Cookie: cacod_back=1.fake'` 应被拦(HMAC 防伪)
3. 真实放行: 登录后台拿 jar 里 cacod_back, 手动 `-H "Cookie: cacod_back=..."`(jar 域名匹配坑见 SKILL.md)
4. 日志确认: 后台斗篷页 grep rule-tag
5. 测完清 dr_blacklist/dr_cloak_log/dr_cloak_visit, 恢复 enabled=0

## 二、Meta Pixel + Conversions API 回传

### 配置
`dr_settings(k='pixel_config')`: pixel_id / capi_token / test_code / capi_enable / pixel_enable

### 浏览器像素(前端)
- fbq init + PageView/ViewContent/AddToCart; **Pixel ID 从后台配置读取**(模板变量注入), 商品 fbpixel 字段兜底; 关闭开关则不输出整段(php if 包裹)
- 事件 ID: `(new Date()).getTime() + '.' + rand + '.' + rand`(去重)

### 服务端 CAPI(Graph API)
```
POST https://graph.facebook.com/v20.0/{pixel_id}/events?access_token={token}
{"data":[{"event_name":"Purchase","event_time":ts,"event_id":"...",
  "user_data":{"em":sha256,"ph":sha256,"fn":sha256,"client_ip_address":...,"client_user_agent":...,"fbc":...,"fbp":...},
  "custom_data":{"currency":"TWD","value":986.00,"order_id":"H..."},
  "action_source":"website"}]}
```
- **em/ph/fn 必须 SHA256(小写)** 才匹配得上; fbc=fb.1.ts.fbclid(前端 cookie `_fbc`), fbp=浏览器 `_fbp`
- 响应判成功: `events_received >= 1`; 失败看 `error.message`
- test_event_code: 字段 `test_event_code`(测试模式, 生产留空)
- 多像素: 前端 fbpixels 数组 → 循环 pixel_send_capi_to(每个像素一次 POST)
- 触发: 下单成功 order_buy 里 `pixel_purchase()`(服务端直发, 不依赖浏览器); 前端 sendBeacon 的 dr_facebook 接口也转发(带哈希)
- 落库 `dr_fb_event` 加 `capi_status` 列(sent/fail/skipped + 摘要), 后台日志页展示
- SSL 上下文: `verify_peer=false`(自签环境), timeout=8s, ignore_errors

### 上线注意
- CAPI token 在 Meta 事件管理工具 → 设置 → Conversions API 生成(用户自备)
- 测试链路: 后台「发送测试事件」按钮 → POST TestEvent → 显示 events_received
