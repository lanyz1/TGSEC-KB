# XunRuiCMS(迅睿CMS)二开 长安COD 商城 — 全站逆向与重建(zengda.shop, 2026-08)

COD 货到付款商城(台湾市场保健品),基于 **XunRuiCMS 4.x(CodeIgniter 3.1.13)二开**,二开品牌"长安COD"(页面注释 `<!--使用长安COD系统搭建，了解更多+v:qwnmdxp-->`,错误页链接 `https://v1v1.cacod.net/`)。

## 识别信号(快速判定)

| 信号 | 含义 |
|---|---|
| `Set-Cookie: csrf_cookie_name=<32hex>` | CodeIgniter 3(XunRuiCMS 4.x 基座) |
| 路由 `index.php?s=模块&c=控制器&m=方法` | XunRuiCMS query-string 路由 |
| `/static/assets/js/cms.js` 的 `dr_` 前缀函数(dr_lang/dr_strtotime/dr_tips) | 迅睿官方前端库 |
| 页面注释 `<!--使用XX系统搭建，了解更多+v:微信-->` | 二开品牌标识(长安COD/其他) |
| 前端 Vue2.7 + Vant + Tailwind + FingerprintJS + vue-seamless-scroll | 典型 COD 落地页栈 |
| `cdnap.cloudflont.top/v1v1s3/202607/xxx.webp` 图床 + `staticapac.rdian.net` 静态CDN | 长安COD 公共资产(多商家共用) |

## CSRF(下单类 POST 必带)

- cookie `csrf_cookie_name` 与 POST 字段 `csrf_test_name` 值相同(32hex)
- 每次刷新页面下发新值;每次 POST 成功后服务端刷新 token,响应 `res.token = {name, value}` 由前端回写隐藏字段
- 采集流程:先 GET 首页拿 cookie+字段 → 同 cookie jar POST

## 核心 API 契约(全部实测)

### 商品(pro)
- 落地页:`GET /index.php?s=pro&c=show&m=index&id=61`;伪静态 `/c7f39f8317` 等价(32位 slug 存于 url_slug 字段)
- 浏览量 JSONP:`GET /index.php?s=api&c=module&siteid=1&app=pro&m=hits&id=61` → `callback({"code":1,"msg":"287705","data":[]})`(msg=浏览量)
- 分类:`?s=pro&c=category&m=index&id=1`

### 下单(order)
```
POST /index.php?s=order&c=order&m=buy&mid=pro&id=61&sku=0_0&num=1&huilu=1&ccode=tw
Content-Type: application/x-www-form-urlencoded
```
GET 参数:mid(模块目录)/id(商品ID)/sku(SKU key `组ID_选项ID`)/num/huilu(汇率)/ccode(国家码)
POST 字段:csrf_test_name + paytype=nopay(货到付款)+ data[name]/data[phone]/data[city](region_id)/data[address]/data[address2]/data[housenumber]/data[remark]/data[youxiang]/data[whatsapp]/data[line]/data[zipcode*]/data[huobi](NT$)/data[abchanpin]/data[laiyuan]/data[gjcs]/data[pydqyf](运费)/data[wuliufangshi](物流)/data[fingerprint]/data[timezone]/data[dr_paste_count]/data[dr_has_large_paste]/data[dr_form_fill_time]/data[dr_total_input_count]/data[dr_page_stay_time]/data[dr_form_source] + coupon

成功响应:
```json
{"code":1,"msg":"success","token":{"name":"csrf_test_name","value":"<新token>"},"data":{"url":"/index.php?s=order&c=order&m=buysuccess&mid=pro&id=61&sku=0_0&num=1&ccode=tw&comb=0&pydqyf=0&ordata[sn]=H2608191945496097&ordata[inputtime]=1787139924&ordata[name]=[xss_clean]&...&coupon=0","time":1787139924}}
```
错误响应:`{"code":0,"msg":"Submit too fast","data":[]}`(IP/session 级防刷)、`{"code":0,"msg":"付款方式不存在"}`、`{"code":0,"msg":"請輸入姓名","data":{"field":"name"}}`(field=定位表单字段)
姓名/地址等字段服务端 xss_clean,回显 `[xss_clean]`。台湾手机 `/^(09|9)\d{8,8}$/`。

### 成功页(buysuccess)
`GET /index.php?s=order&c=order&m=buysuccess&mid=pro&id=61&...&ordata[sn]=Hxxx` — Nuxt SSR 风格订单确认页(订单号/地址/商品/金额明细),**订单数据明文走 GET,知道订单号即可查看**(无签名校验)。

### 地区联动(api)
- 扁平列表:`GET /index.php?s=api&c=api&m=linkage_ld&mid=order&file=&code=tw[&parent_id=403]` → `{"data":[{"region_id":"403","region_code":"nantouxian","region_name":"南投縣","region_zipcod":""}]}`
- 三级树 JS:`GET /index.php?s=api&c=api&m=linkage&code=tw` → `var linkage_tw =[{"value":"403","label":"南投縣","children":[...]}]`
- code 取值:tw(宅配)/tw711(7-11)/twqj(全家)/twhls(黑猫)/hksf(香港顺丰)/hk/sg/my/us;cn 空=不配送大陆
- 规模:tw 401 条、tw711 7468(门市)、twqj 4874、twhls 2074、hksf 437(共约 1.5 万)

### 其他
- 验证码:`GET /index.php?s=api&c=api&m=captcha` → image/png
- 模板渲染:`GET /index.php?s=api&c=api&m=template&name=checkout.html` — 可枚举模板名;已配置的渲染真实内容,未配置 fallback 信息页(名称探测不可靠,只看实际使用的)
- 埋点:`GET /index.php?s=weblog&url=...&cpu=30&stayTime=10&event=view30&title=...&uid=14&thumb=577&citycode=tw&useformData=...`(JSONP;event:view30/view60/view90/hidden/addtocart/purchase/searchzipcode/contact/phonepaste/namepaste)
- FB CAPI:`POST /index.php?s=ip_cz&c=home&m=dr_facebook` body `{"eventData":{...}}`(sendBeacon,多像素:FB/TikTok/Snap/Kwai/Taboola/Google)
- 标准接口:`s=api&c=api&m=pinyin`/`ip_address`(二开魔改返回"IP库不存在")/`checktitle`/`getkeywords`;`s=api&c=file&m=file_delete`(危险,需鉴权);`s=member&c=register`(商家可关:返回"系统没有可注册的用户组")

## 订单号 / 数据格式

- 订单号:`H` + yymmddHHMMSS + 4位随机(如 H2608191945496097)
- 埋点参数:uid=站点UID(14)、thumb=模板ID(577)服务端注入页面
- 物流方式 wuliufangshi:1=宅配 2=7-11 3=全家 4=香港顺丰 5=黑猫(联动 code 对应 tw/tw711/twqj/hksf/twhls)
- 商品 SKU JSON(内联 data() 里):group{组ID:组名}/name{组ID:{选项ID:名}}/image/value{key:`组ID_选项ID`:{image,price,yprice,quantity,sn}}/demoname(默认选中)/fbpixel数组/huobijx(TWD)

## 后台面

- `admin.php` 及 30+ 常见变体全 404(9字节标准404);`index.php?c=admin` 302→/404.html
- 子域全 wildcard 泛解析:HTTP 探测返回 530=不存在(不能只看 DNS)
- 错误页回链 `v1v1.cacod.net` 已死链(404)→ 真正后台在独立域名/隐蔽路径,需证书透明度或卖家信息
- 重建版自带后台:`/index.php?s=admin&c=order&m=index`(登录 admin/admin123,订单 CRUD+状态+埋点日志)

## 重建复刻要点(用户"源码丢了要恢复"场景)

1. **框架基线**:XunRuiCMS 官网 https://www.xunruicms.com/down/ 免费;gitee 正确仓库 `dayrui/xunruicms`(不是 xunruicms/xunruicms),zipball 下载需登录,github 直连常被墙
2. **前端**:线上 HTML 完整抓取(商品页 134KB 含内联 Vue2 全部逻辑)→ 转本地模板,动态数据(sku_json/hits/pixel/weblog uid)PHP 注入;静态资源 CDN 本地化
3. **后端**:原生 PHP8 + SQLite 复刻路由格式,零依赖可跑(`php -S 127.0.0.1:8080`)
4. **地区库导入**:JS 树 → SQLite 扁平表(展开 children,记 parent_id),linkage_ld 按 parent_id 查、linkage 重建树
5. **表结构**(重建推断):dr_pro(id/url_slug/title/thumb/sku_json/hits/fbpixel)、dr_order(sn/inputtime/proid/sku/num/name/phone/city/address/.../status)、dr_linkage(group_code/region_id/region_name/parent_id)、dr_weblog、dr_fb_event
6. **seed 注意**:商品 id 要与线上 API 参数一致(接口按 id=61 查,自增 id=1 会查不到)

## 重建坑(实测)

- 控制器方法名 = `c_m`:`s=pro&c=show&m=index` → `show_index()`,不是 `pro_show()`
- HTML 转 PHP 模板:`tcskuData: {` 含子串 `skuData: {`,字符串 replace 会误替换 → 用正则 `(?<!tc)skuData: {` + 括号深度配对
- Python 替换产生 `\$pro[\'id\']` 反斜杠 → 只在 `<?php...?>` 段内清理,勿动 JS 合法 `\'` 转义
- Windows 原生 curl 写中文路径(D:\渗透\...)失败 → 先下英文 ASCII 路径再 cp
- `var linkage_tw =[` 等号后无空格 → 正则 `var \w+\s*=\s*(\[.*\]);`
