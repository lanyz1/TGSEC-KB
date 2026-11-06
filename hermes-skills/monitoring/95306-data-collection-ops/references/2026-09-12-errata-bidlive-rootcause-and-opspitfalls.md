# 2026-09-12 勘误与运维小坑(增量补记)

## 勘误: 2026-09-11-bidlive-capture-v927-fix.md 的"待验"节
- 该节"若日志仍全灭 → 下一迭代 = 竞价室进场票源挖掘(参与方票假设)" **已失效(09-12 定论)**。
- 定论: `/bidRoom/initProjInfo`(`/bidMonitor/*`) = **员工功能**(cg 工作台内部房控), 供应商票无论是否参与方均 500/100 不通; 乌局72(09-12) v9.27 部署后实战仍全灭。
- 真实通道 = ①内部员工会话(特权线 priv_loop 在撞) ②供应商侧房接口(bid2: compete/manage/allProject、deal/reverseBidResult?token=, 待验)。详见 references/2026-09-12-bid2-jwt-harvest-and-ticket-rules.md §4。
- cg 探测头铁律: 必须带 Referer `https://cg.95306.cn/bfwz-view/`(不带会误报"没有该功能的操作权限", 别据此判死); 错误类含义见 09-12-bid2 ref §4。

## 运维小坑
- **sed 派生 runner 先核对替换目标**: 由旧 runner `sed 's/qNNNm/qNNNm/'` 派生时, 若源文件不含该标记(上传路径写死等)则产出=原样副本 → 静默重跑上一次动作(**曾误重发全队部署**)。派生后 diff 确认再跑。
- write_file 分片拼接必须显式补换行: `for f in a1 a2; do cat "$f"; echo; done > out`(纯 cat 会粘连尾行 → SyntaxError)。
- auditlog 审计流为**近实时(分钟级)**(非 2h 延迟); 用其看进度可直接看最新行 operation_time。
