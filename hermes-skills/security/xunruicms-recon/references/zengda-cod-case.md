# zengda.shop 实战案例(长安COD / XunRuiCMS 二开)

2026-08-19 逆向记录。目标: https://zengda.shop/c7f39f8317(台湾男性保健品 COD 落地页, 站主自站源码恢复)。

## 资产拓扑

| 项 | 值 |
|---|---|
| 主站 | zengda.shop(Cloudflare) |
| 静态 CDN | staticapac.rdian.net(公共, 多长安COD站共用) |
| 图片 CDN | cdnap.cloudflont.top/v1v1s3/(S3 风格 bucket, 路径含日期 202605/202607) |
| 系统商痕迹 | 页面注释 `<!--使用长安COD系统搭建，了解更多+v:qwnmdxp-->`; 错误页返回链接 v1v1.cacod.net(404 死链) |
| 框架 | XunRuiCMS 4.x(CI 3.1.13), 前端 Vue2.7.14 内联 + buysuccess 页 Nuxt SSR |
| 子域 | 全 wildcard DNS → HTTP 530(不存在) |

## 已确认接口(全部实测)

| 接口 | 方法 | 说明 |
|---|---|---|
| `index.php?s=pro&c=show&m=index&id=61` | GET | 商品落地页(= `/c7f39f8317` 伪静态, 134KB 完整页) |
| `index.php?s=api&c=module&siteid=1&app=pro&m=hits&id=61` | GET | 浏览量 JSONP: `callback({"code":1,"msg":287705})` |
| `index.php?s=api&c=api&m=linkage&code=tw` | GET | 三级联动树 JS 变量 `var linkage_tw=[...]` |
| `index.php?s=api&c=api&m=linkage_ld&mid=order&code=tw&parent_id=403` | GET | JSON 地区 `{data:[{region_id,region_code,region_name,region_zipcod}]}` |
| `index.php?s=api&c=api&m=captcha` | GET | PNG 验证码 |
| `index.php?s=api&c=api&m=template&name=checkout.html` | GET | 模板渲染(未配置名 fallback 信息页) |
| `index.php?s=order&c=order&m=buy&mid=pro&id=61&sku=0_0&num=1&huilu=1&ccode=tw` | POST | **下单(实测成功)** |
| `index.php?s=order&c=order&m=buysuccess&...&ordata[sn]=H2608191945496097` | GET | 下单成功页(Nuxt SSR) |
| `index.php?s=order&c=order&m=pay&mid=pro&sn=H...` | GET | 支付页("订单参数不存在"/"订单[H...]状态不正确") |
| `index.php?s=weblog&url=...&cpu=&stayTime=&event=&uid=14&thumb=577&citycode=tw` | GET | 行为埋点 JSONP(uid=站点ID, thumb=模板ID) |
| `index.php?s=ip_cz&c=home&m=dr_facebook` | POST | FB CAPI 代理(sendBeacon JSON `{eventData:{...}}`) |
| `index.php?s=member&c=register&m=index` | GET | 注册页(提示"系统没有可注册的用户组"= 关闭) |
| `index.php?s=api&c=api&m=ip_address&value=8.8.8.8` | GET | 返回"IP归属地：IP库不存在"(二开魔改, 含 `action=cacod` 参数) |

## 下单请求/响应实录

请求 POST 字段: `csrf_test_name`(=cookie `csrf_cookie_name` 值) + `paytype=nopay` + `data[name/phone/city/address/huobi/abchanpin/laiyuan/gjcs/wuliufangshi/pydqyf/fingerprint/timezone/dr_*]` + GET `mid/id/sku/num/huilu/ccode`。

成功响应:
```json
{"code":1,"msg":"success","data":{"url":"/index.php?s=order&c=order&m=buysuccess&mid=pro&id=61&sku=0_0&num=1&ccode=tw&comb=0&pydqyf=0&ordata[sn]=H2608191945496097&ordata[inputtime]=1787139924&ordata[name]=[xss_clean]&ordata[phone]=0912345678&ordata[city]=405&ordata[address]=[xss_clean]&ordata[address2]=&ordata[housenumber]=&ordata[remark]=&ordata[gjcs]=tw&coupon=0"}}
```

要点:
- name/address 被 `xss_clean` → 显示 `[xss_clean]`
- 订单号 = `H` + yymmddHHMMSS + 4随机
- 前端 2s 后跳转 data.url; 表单错误返回 `data.field` 定位
- 限速错误 `{"code":0,"msg":"Submit too fast"}` — 新 GET 刷新 CSRF 后重试成功
- 缺 paytype → "付款方式不存在"

## SKU 数据结构(服务端注入内联 JS)

```javascript
skuData: {
  yunfei: 0, proid: '61', moddir: 'pro', huobi: 'NT$', huilu: '1', ccode: '',
  fbpixel: ['2804301909969717'], myWebUrl: '...', countryIp: '<访客IP>',
  huobijx: 'TWD', thumb: '<主图webp>',
  group: {'0':'套餐名'},
  name: {'0':{'0':'（2盒基礎裝960NT$）...','1':'（4盒治療裝1360NT$）...','2':'（6盒至尊套裝1860NT$）...'}},
  image: {'0':{'0':'','1':'','2':''}},
  demoname: ['0'],
  value: {'0_0':{image,price:'986',quantity:'1000',sn:'',yprice:'2980'}, '0_1':{...1386/3980}, '0_2':{...1886/5980}}
}
```
SKU key = `groupIds.map((g,i)=>g+'_'+selectedOptions[i]).join('_')`。

## 物流方式与 code 对应

`wuliufangshi`: 1=宅配(tw) 2=7-11(tw711) 3=全家(twqj) 4=香港顺丰(hksf) 5=黑猫(twhls)。地区数据量: tw 20KB / tw711 546KB / twqj 389KB / twhls 174KB / hksf 50KB。

## 商品 ID 与模块结论

- pro 模块商品 ID(200 内): 17,19,21,22,26,30,33,34,37,48,49,50,51,52,53,61-65,67-84(约 37 个, 采样确认 62=SST V3X黑金魔 / 70=斑龍丸 / 80=固威寶)
- 模块清单: pro/order/pay/member/api/weblog/ip_cz/news(news 空)
- 后台: admin.php + 30 变体全 404, 未找到(诚实收尾, 建议站主自查)

## 交付物(站主源码恢复)

`D:\渗透\zengda_recon\`: README.md + docs/API.md + templates/(页面 HTML) + js/ + css/ + data/(全量地区库) + modules/(路由渲染采样)。重建路径: XunRuiCMS 4.x 官方框架(www.xunruicms.com/down/, gitee/github 直连常被墙) + 本文档契约重写业务模块。
