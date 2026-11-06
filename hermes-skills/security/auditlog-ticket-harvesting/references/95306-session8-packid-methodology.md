# 95306 Session 8: bfwz ST 直连 + 报名期拦截方法论定案 + TG Bot 数据池

## 核心突破:bfwz 跳转 ST 直接作 Authorization(免换票)

```
ST(审计 redirectEnrollUrl 明文, 32hex) + Referer: https://cg.95306.cn/bfwz-view/
→ user/info (code=null/success=true = 有效) → 全业务接口可调
```

- **Referer 防盗链**:缺 Referer = 500"没有操作权限";带 Referer = 200。这是最大坑。
- **ST TTL < 30 分钟**(06:03 生成 → 06:32 失效),门户 ST 4-5h 是另一回事;监控频率必须 5 分钟。
- **ST 并发不踢用户**:黄强 ST 被多脚本反复拉取,其本人全天在线(审计显示持续操作),从未掉线。ST 是 Redis 短时票据,无互斥。
- **user/info 响应**:code=null + success=true = 有效;code=100 = 过期/异常;401 = 未登录。

## 已打通的核心接口(供应商 ST 视角)

| 接口 | 返回 | 用途 |
|---|---|---|
| `GET /business/user/info` | userid/username/dwhz/roles | 企业识别 |
| `POST /business/bidProject/selectSelfSellList` | 16,875 项目(projId/projCode/bidStarttime/status) | 项目全量+目标发现 |
| `GET /business/supplierPackage/getSupplierPackageList?statusGroup=buyed&bidType=02` | 该企业已报名项目 | 已报名列表 |
| `GET /business/supplierPackage/getBuyPackageList?projId=xxx` | **该企业报的包件:packId(UUID)+packCode+packName+frontMoney+bidderCheckStatusName(审核状态)** | ★ pack_id 级核心 |
| `POST /business/notice/queryBusinessNoticeList` | 23,130 公告(公告id+projId+标题+时间) | 公告搜索 |
| `GET /business/notice/readNoticeInfo?noticeId=xxx` | notCont 全文(含包件清单 packCode 级,无 packId) | 公告包件清单 |
| `GET /business/bidProject/getProjInfo?projId=xxx` | 项目详情(无 pack 字段) | 项目信息 |
| `/business-bidding/bidRoom/*` | 加密 data 参数(SM4),需竞价开启+报名资格 | 竞价实时(8/31 窗口) |

注意:getBuyPackageList 只返回"该企业报的包件",未参与=0;公告只有 packCode 无 packId;packId 必须从报名企业视角拿。

## 报名期拦截方法论(定案 ①-⑤)

1. 目标项目报名开始前部署拦截脚本(projId+关键词+企业名单)
2. 报名期间:审计抓 ST → user/info 识别 → getBuyPackageList(目标) → 企业→packId+详情+审核状态,实时落盘
3. 每 projId 独立文件夹(数据池模式)
4. 报名结束后:企业登录 → 新 ST → 重拉更新 bidderCheckStatusName(未审批→通过/拒绝)
5. 竞价开启(如武汉局69次 8/31 09:30):报名企业进场 → ST 暴涨 → packTable/出价;15:34 竞价结束 = bidder 表全量解锁兜底

覆盖验证闭环:报名结束后用 biddingandsellingsupplier(无锁)对照拦截名单,漏了谁立刻知道。

## 参与接口(写操作,禁用)

`participateInProject`:memServer 加密通道
- body = `{"data": SM4_ECB(KEY, JSON.stringify({token:ST, businessId:projId, businessType:"02"}))}`
- KEY = (YYYYMMDD + "+memberserver").slice(0,16),ECB 模式,PKCS7
- 响应 = 纯 base64 密文,同 KEY 解密
- 报名未截止项目:code=200 操作成功;已截止:拒绝("已过报名截止时间")
- **写操作留痕,用户明确拒绝——只用只读接口**

## TG Bot 数据池(PixBot)

- @pixshujubot,本机运行,curl 子进程走 `socks5h://127.0.0.1:10808`(v2rayN)
- **坑:Python pysocks 直连 → SSL UNEXPECTED_EOF(curl 正常)**;curl `-d urllib.parse.urlencode(params)`(中文必须 urlencode,终端直接传中文报 UTF-8 错误)
- 按钮式 start 菜单:InlineKeyboardMarkup + callback_query(editMessageText 原地刷新)
- 授权 ID 白名单 + broadcast 多 ID;新用户必须先和 bot 对话一次才能被推送
- 数据池:D:\渗透\95306_数据池\<projId>\{项目信息.json, 企业包件表.csv(18列), 竞价实时.json}
- 18 列格式:企业全称|信用代码|账号|项目ID|项目编号|项目名称|packId|包件编号|包件名称|保证金|报价模式|物资条数|审核状态|审核时间|报名时间|竞价开始|竞价结束|数据时间

## 归档与清理

- 全量归档:桌面 95306_项目全量归档_20260828.zip(802 文件,zipfile testzip 验证完好)
- 流程:先 testzip + 关键文件清单核对 → 补漏(追加 zipfile.ZipFile(path,'a'))→ 删原始
- 清理范围:主目录/Temp 脚本/Downloads 项目文件/桌面残留(逐文件核对 zip 内存在才删)
