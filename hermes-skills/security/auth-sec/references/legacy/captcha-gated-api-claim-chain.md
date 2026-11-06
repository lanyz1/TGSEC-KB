<!-- archived from /root/.hermes/skills/security/captcha-gated-api-claim-chain/SKILL.md on 2026-10-21 -->

---
name: captcha-gated-api-claim-chain
description: "Use when 领奖端点被环境字段闸门+图像点选验证码挡住。"
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
---

> 归档卡：原目录 `/root/.hermes/skills/security/captcha-gated-api-claim-chain`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/captcha-gated-api-claim-chain/…')`，不要相对 `references/legacy/` 解析。

# 验证码闸门型领奖/解锁链(加密 API 资金面)

同进程一气跑完 `open → verify×N → claim`,并在进程内自动解挑战。

## 触发
授权目标的「领奖 / 解锁红包 / 提现 / 免费领取」端点已经可达、token 也合法,但:
- 端点**永远回同一个笼统码**(如 `40671 解锁链接无效` / `40709 请先完成验证` / `参数错误`),不告诉你缺什么;
- 或已拿到 `session_id`,提交时却回**会话失效**;
- 伴随**图像点选验证码**(目标图标 + N×N 网格 / 滑块)。
目标侧若有专用技能卡(如 `tma-encrypted-api-reverse`)先读它拿该站契约,本卡管**方法论与铁律**。

## 铁律(顺序即优先级)
1. ★★★ **同码 ≠ 目标防住了,而是前置闸门未越过。** 笼统同码时停止喷涂候选字段,回到 bundle 读 wrapper 的**调用点**取真实 body(取法见 `spa-request-contract-extraction`)。
2. ★★★ **自报字段里只有「服务端能独立观测」的那条是真闸门。** 一包环境字段(`user_agent` / `device_hash` / `device_profile` / `automation_*` / `client_ipv4`)中,指纹与声明可缺省、可伪造(客户端本就会因指纹库失败而不发),但 **`client_ipv4` 会被服务端与请求源 IP 对账**:漏它 ⇒ 永远同码;**补成自己的真实出口 IP** ⇒ 首打即通。走跳板/代理时用**跳板出口 IP**(ipify / icanhazip / ip.sb 三备探测),**绝不自报一个不是自己的 IP**——那是唯一能被独立抓住的破绽。
3. ★★★ **一次性票据 + 短 TTL ⇒ 全链必须同一进程一气跑完。** initData/一次性票据**只能握手一次**(多形态扫描共用一份 ⇒ 除首发外全是**假阴性**);会话密钥只活在发起握手的进程里。实测 `open` 后 **~60–75s 即会话失效** ⇒ **handshake → open → verify×N → claim 一条命跑完**;拆进程、或人肉在环(看图→推答案→再发,~75s)**必然超时**。
4. ★★★ **答案必须在进程内自己算出来,不能靠人。** 挑战图 = 顶部目标图标 + 下方 N×N 网格,**服务端把颜色随机化** ⇒ 只能按**形状**匹配(目标格与答案格尺寸朝向一致、仅配色不同)。用 `scripts/seg_solve.py`(最频背景色 → 行/列投影切盒 → 前景二值化裁内容 bbox → **保长宽比填充** 128×128 → IoU → 取最大)。**必须保长宽比**:填充式归一化会把「宽扁形 vs 竖高形」压成同形(实测冠军差距被压到 0.012);再加**置信门槛(最佳≥0.70 且与亚军差≥0.10)**,不达标才回退人工读图。
5. ★★ **远程模板复用只读脚本的协议层原文。** 把已验证的**只读**模板按 `def main():` 切两半,前半(imports/常量/ECDH/HMAC/请求封装)**逐字复用**,只换 main ⇒ 协议层零回归。占位符注入后 `count==1` 自检 + 注入后逐字回验。
6. ★★ **只写「写完即走」的最小不可逆动作**:资金动作只做用户点名的那一个对象,其余一律只读验证。

## 流程
1. **契约**:bundle 取真实 body 字段表 → 按铁律 2 排优先级(先补服务端可观测字段)→ 打一发看错误码是否跳阶。
2. **判解锁**:`open` 类端点回 **200 + `session_id`** 即通关;响应会带 `min_interval_ms`(如 1200,提交按它节流)与挑战 `segment`。
3. **定挑战契约**(bundle 里的客户端校验式就是权威):`segment = { grid_size∈[4,9,16], index(0基), total≤8, challenge_id(非空), image_width=600, image_height=720, grid_top=120, image_data="data:image/png;base64,…" }`;提交 `{session_id, challenge_id, index, answer:<点选格序号>}`;**全部段过完**才允许 claim。
4. **跑链**(同一进程):`open` → 对每个 index:存图 → `solve()` 出答案 → 按 `min_interval_ms` 节流 → verify → 下一段(响应带了下一段就继续)→ 全过完再 `claim` → 复读一次后态。
5. **兜底(自动解不置信时)**:远端长驻进程守链,每步把挑战图落远端文件并**轮询 `ans_<index>.txt`**;本机 driver 经 **sftp** 取图、推答案(paramiko 长连)。读到的答案文件**立即 `os.remove`**,否则陈旧答案会被下一步复用。人类在环只做兜底。
6. **收尾**:把「哪一发成功/哪些是假阴性」写进档案;同一个包只领一次,别重复打。

## 坑位
- **假阴性三件套**:共用一次性票据做多变体扫描 / 没等握手成功就判 open 不行 / 把**通道级**拒绝(如 `DataInvalidError`、笼统同码)读成「目标防住了」。凡负结论先做正控。
- **进程/日志**:跳板机 `exec_command` 里用 `&` 起后台会被继承的 fd 拖住 ⇒ 通道读 `socket.timeout`(加 `</dev/null` + 只读循环容错,**别把超时当启动失败**);远端/本地 python 把 stdout 交给缓冲时**日志 0 字节 ≠ 卡死**,进度要**直接写文件**、靠文件时间戳判存活。
- **人类只许「看图」不许「参与时序」**:人工只在兜底路径喂答案,不得让资金动作等人工。
- **`verify` 回会话失效 ⇒ 直接重铸 + 重开链**,别在旧会话上重试、别把失效读成「答案错了」。
- **图形挑战不做 OCR/文字识别**:它是**纯形状**问题,颜色是噪声。
- **进度别靠 stdout 翻页看**:每步落一行 JSON 到日志文件,同一条命里同时记录 `phase/i/answer/http/code`。

## 交付
- 战报写清:前置闸门的**字段表**(哪些可缺省、哪个是硬闸门)、挑战**逐段答案与依据**(可复核的 IoU 分数)、`min_interval_ms` 与会话 TTL 实测值、最终业务态(余额/领取记录)。
- 挑战图与解答留档(工作区 + 档案 + 桌面),便于复核「不是猜的」。

## 脚本
`scripts/seg_solve.py` — 图标网格挑战的形状匹配求解器(PIL+numpy)。`python3 seg_solve.py <png> [grid_size]` → `BEST=<序号或None> SCORES=[...] META={margin}`;`None` = 置信不足,回退人工。
