## 公告全文补拉

- collector 按标题搜 queryBusinessNoticeList 找 noticeId 会漏(翻页/超长标题)
- **正确做法:/data_pool/notices_map.json(noticeId→projId,merger 自愈维护)反查 → readNoticeInfo?noticeId= 直拉**
- 清理:先去 <style> 块再删标签;CSS 残留是首行含多个 { } → 裁到第一个 \n

