# gofile 入站协议细节（2026-10-17 实测）

场景：用户把 118MB 报告包放 gofile，Telegram 入站 20MB 硬墙挡住，机器人自己拉。

## 端到端命令形态

```bash
# 1) 游客票
tok=$(curl -s -X POST https://api.gofile.io/accounts \
  -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0' \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["data"]["token"])')

# 2) 清单（wt 用 Node 现签，见 gf_wt_solve.mjs / scripts/gofile_fetch.mjs）
curl -s https://api.gofile.io/contents/<contentId> \
  -H "Authorization: Bearer $tok" \
  -H "X-Website-Token: $wt" -H 'X-BL: en-US'

# 3) 下载（必须带票）
curl -sL -H "Authorization: Bearer $tok" -o out.bin "$store_link"
```

## 观测到的 payload

- 正常：`{"status":"ok","data":{... name,size,md5,link ...}}`；单文件时 `children` 为空。
- 私有：`{"status":"ok","data":{"canAccess":false,"public":false}}` → `notPublic`，用户开 Public 即修。
- wt 放 query：`error-notPremium`（误导；改请求头后消失）。

## 前端源码地图（要再逆向从这进）

| 模块 | 作用 |
|---|---|
| `/js/services/contents.js` | 真协议出处：`X-Website-Token` + `X-BL` 请求头 |
| `/js/core/wt.js` + `/js/wt.obf.js` | wt 生成逻辑；密钥烘死、服务端约 6h 轮换 |
| `/js/files/manager.js` | gate 分派：password / expire / notPublic / 冷存储 |
| `/js/files/templates.js` | 冷存储文案（导入需 Premium） |

## 踩坑记录

1. 硬编码 wt（`4fd6sg89d7s6` 之类）早已失效 → 必须动态签。
2. wt 传 query → 401 / error-notPremium；传请求头 → 200。
3. 老分享可能 `status: ok` 但无数据（`children: 0` 且无 name）—— 那是真空分享，与私有态区分开。
4. `/download/web/<cid>/x.bin` 假文件名会被弹回 SPA；真名在 `data.name`。
5. 本机可用脚本：`/root/tgsec-ingest/gf_fetch.mjs`（实测通过）、`/root/tgsec-ingest/gf_wt_solve.mjs`。
