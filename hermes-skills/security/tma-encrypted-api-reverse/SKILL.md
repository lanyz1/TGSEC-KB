---
name: tma-encrypted-api-reverse
description: Use when 打 TMA 自研加密 API:ECDH/AES-GCM/HMAC+initData。
---

# TMA 加密 API 逆向与合法身份攻击

<!-- split-index -->

## Section index

- [触发](references/split-01-section.md)
- [四步法(顺序不能乱)](references/split-02-section.md)
- [initData 时效铁律](references/split-03-initdata.md)
- [可攻击点(拿到合法身份后)](references/split-04-section.md)
- [TG 侧硬限制(省时间)](references/split-05-tg.md)
- [反侦察/蜜罐识别](references/split-06-section.md)
- [bot 侧(= "Web 之外的管理端")实测手法](references/split-07-bot-web.md)
- [收尾](references/split-08-section.md)
- [★★★★ POST 体必须加密 —— 「安全信道未建立」的真凶（2026-09 增补，踩了 4 轮）](references/split-09-post-2026-09-4.md)
- [★★ 领取链(open → verify-segment×N → claim) + 图形挑战自动秒解](references/split-10-open-verify-segment-n-claim.md)
- [载具 / 编码 / 通道 —— 判读铁律（负结论前必跑正控）](references/split-11-section.md)
- [★★ 诱饵基线 · 同族开源审计 · 成品结果回收（2026-09 实战增补）](references/split-12-2026-09.md)
- [★★ bot 内联键盘状态机 + 业务限制「四组对照」测绘（2026-09 实战增补）](references/split-13-bot-2026-09.md)
- [★★★ 「到确认页」≠「服务端缺校验」（实证反证 · 2026-09 增补）](references/split-14-2026-09.md)
- [★★★ 路由面「穷尽」判定：方法矩阵 / 异常码 / 主机名 oracle（2026-09 实战增补）](references/split-15-oracle-2026-09.md)
- [★★★ 签名分隔符以「差分矩阵」定案 · 响应体密文 · token 闸门在握手（2026-09 增补）](references/split-16-token-2026-09.md)
- [★★★ 铸票 fragment 解析 + token「不可伪造」变异矩阵（2026-09 增补，独立复跑实证）](references/split-17-fragment-token-2026-09.md)
- [★★★ 路由 oracle 的「时变性」：多副本/灰度 + 探针自证（2026-09 增补，推翻单次观测）](references/split-18-oracle-2026-09.md)
