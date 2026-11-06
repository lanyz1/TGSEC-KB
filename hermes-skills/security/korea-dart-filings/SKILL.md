---
name: korea-dart-filings
description: Use when researching Korean companies via DART filings.
---

# 韩国 DART 公示挖掘（dart.fss.or.kr）

## 何时用
任何韩国公司深调：交易条款（CB/EB、股权、担保）、子公司结构、合同、高管实名。DART 原始公示含金额/对手方/条款全文，通常比媒体稿详细一个量级。实战例：LS에코에너지 越南稀土链（8 份公示连穿，报告存 /root/research/vietnam-rare-earth/）。

## 流程（viewer 必须走浏览器；同源可读 iframe）
1. `new_tab("https://dart.fss.or.kr/dsab007/main.do")`（공시통합검색）
2. `fill_input("#headTextCrpNm", "회사명")` → `js("headSearch()")` → sleep ~5s
3. 抓行：`a[href*="rcpNo"]` 的 href = `/dsaf001/main.do?rcpNo=14位数字`；**rcpNo 必须 14 位**（regex 清洗易混入前缀，先核对）
4. `goto_url("https://dart.fss.or.kr/dsaf001/main.do?rcpNo=XXXX")` → sleep 5-6s → 读 `js("document.querySelector('#ifrm').contentDocument.body.innerText")`
5. 长报告（반기보고서 等）：点外层目录 `II. 사업의 내용` / `6. 주요계약 및 연구개발활동` 等 → 再读 `#ifrm`
6. **链更早公示**：正文里 `※ 관련공시` 是超链接（openReportViewer('14位')）——顺链接抓第一条结果页之外的历史公示（框架协议原文等）

## 坑（实测）
- rcpNo 错了 → 页面标题「거부」；不是封 IP，是编号错
- dcmNo 由 JS 动态加载，curl 拿不到 → 用浏览器读 iframe（同源）
- 搜索结果只显示最新 ~15 条；`#startDate/#endDate` 用 JS 设置 + headSearch() **不生效** → 翻早只能走 관련공시 链
- Google Patents 全文 API（免 key）：`curl "https://patents.google.com/xhr/query?url=q%3D<关键词>%26assignee%3D<公司>"` 返回 JSON
- ImportYeti 有 CF 墙（headless 过不去）；KOCHAM（kocham.kr）可查在越韩企高管；USGS 国别矿产年报（pubs.usgs.gov/myb）有工厂产能表

## 报告名速查
- 타법인주식및출자증권취득결정 = 购买他公司股权
- 주요사항보고서(전환사채권발행결정) / (교환사채권발행결정) = 发 CB / EB
- 주권관련사채권의취득결정 = 买对方 CB
- 타인에대한채무보증결정 = 对外担保
- 투자판단 관련 주요경영사항 = 重大经营事项（战略合作公告在此）
- 특수관계인에대한출자 = 向关联公司注资
