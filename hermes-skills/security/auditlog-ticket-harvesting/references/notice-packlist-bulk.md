# 公告全链路批量拉包件清单(报名期提前对应包件)

> 2026-08-30 实测。目标:竞价开始前把在网项目的包件清单(公告级 packCode)全量拿到,不依赖竞价室。

## 1. 公告列表(需 ST)

```
POST /business-proxy/business/notice/queryBusinessNoticeList
Body: {"projType":"02","notTitle":"","noticeType":"","dateType":"",
       "pageVo":{"pageNum":1,"pageSize":100},"isjtgsCode":0,"validOr":"1",
       "orderField":"","orderType":"","onweb":"","jointSaleType":"","noticeStatus":""}
响应: data.result[] — id(公告id)/projId/notTitle/pubTime/status/sellEnddate(报名截止)/jointSaleTypeName
总量: totalCount≈23,150
```

- **notTitle 模糊搜索可用**(如"第9次废钢轨"),但留空翻页 + projId 匹配更通用
- 按 pubTime 倒序,在网项目公告集中在最近 30-40 页(40 页×100 匹配到 ~72/115 在网项目)

## 2. 公告全文(含包件清单)

```
GET /business-proxy/business/notice/readNoticeInfo?noticeId=<公告id>
→ data.bidNoticeResultVo.notCont (HTML 正文)
```

包件段正则:
```python
packs = re.findall(r'第(\d{1,3})包[：:](.*?)(?=第\d{1,3}包[：:]|包件具体内容|$)', cont, re.S)
# 名称: r'([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{3,40}?)\s*(?:竞卖保证金|起拍价|竞价)'
# 保证金: r'竞卖保证金[：:]*人民币?([\d.,]+)元'
```

注意:同 projId 可能多条公告(主公告 + 变更/补遗公告,如"关于...的公告"改保证金)——优先拉 notTitle 含"项目公告"的,补遗公告用于覆盖变更。

## 3. 批量落盘(61 项目/224 包件实测)

```
/data_pool/<projId>/包件清单_公告.json
{"projId","公告id","包件清单":[{"packCode","packName","保证金"}],"时间"}
```

限速 0.4-0.5s/次,72 个公告 ~40s 完成。

## 4. 边界(诚实)

- **公告清单 = packCode 级(包号+名称+保证金),无 packId(UUID)**
- **packId 仅企业登录后可见**(getBuyPackageList 返回该企业报的包件);报名期靠审计拦截,报名截止后纯读无通道
- 已截止报名项目(如郑州局9次二次,报名止 8/26,竞价 9/1)→ packId 只能等竞价开启自动捕获
- 报名明细 CSV(277,887 条,8/28 导入)可查历史报名企业(bidder_name/un_social_cr_code/buy_time),但**不含 packId**,且二次项目可能无企业记录
