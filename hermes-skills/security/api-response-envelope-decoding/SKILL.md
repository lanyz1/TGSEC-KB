---
name: api-response-envelope-decoding
description: Use when API responses are wrapped and scans hit 0.
version: 1.0.0
tags: [api, base64, envelope, false-negative, triage]
---

# API 响应包络解码与假阴性回扫

**一句话**：`data` 字段是字符串而不是 JSON 对象时，你拿到的不是数据，是一道算术题。
算错了不会报错，只会给你一个漂亮的「0 命中」。

**触发**：批量扫描 0 命中 / `json.loads` 在整批响应上失败 / `data` 是 `str` /
同一接口手工请求正常但脚本全空 / 前一阶段得出过「服务端没有明文」这类阴性结论。

## 一、先判定这是包络问题

| 信号 | 读数 |
|---|---|
| 响应体 `{"code":200,"data":"eFd4Sj..."}` | `data` 是 base64 文本 ⇒ 至少一层 |
| 解一层得到 ASCII 文本而非 `{` | 双层（外层是前缀或包裹，内层是 base64 文本） |
| 解出来是 `\x1f\x8b` | gzip 层，先 `gzip.decompress` |
| 解出来是高熵二进制 | AES；密钥去前端 bundle 找（配合 `api-crypto-analysis`） |
| 整批 `data` 都能解但要搜的字段全空 | **解码器结构错了，不是数据没有** |

## 二、包络家族（按出现频率）

1. **定长前缀 + base64(JSON)**：`base64(<1 字节> + base64(JSON))`。最常见，但**前缀长度会变**。
2. **随机长度前缀 + base64(JSON)**：`base64(<N 字节随机> + base64(JSON))`，N 每发不同（实测 0/1/25/28）。
   ⇒ **不能按固定长度切**，必须 offset 扫描。
3. **AES-CBC/ECB 包 JSON**：`base64(iv || ct)`，密钥硬编码在 bundle（见 `api-crypto-analysis`）。
4. **gzip + base64**：`base64(gzip(json))`。

## 三、通用解码器（offset 扫描）

不要写「按第 1 字节切」的版本。用 `scripts/decode_envelope.py`：对每层枚举 0..48 偏移，
取**第一个能解析出 `{"` 开头 JSON 的切片**，并返回命中偏移（偏移本身是接口指纹）。

```python
from decode_envelope import decode_data, calibrate
d = decode_data(resp.json()["data"])   # dict/list 或 None
if d is None:                          # 解不出来，不要当成「无数据」
    ...
```

## 四、校准纪律（三条，缺一条结论就是废的）

1. **已知成功请求先过一遍**：拿一个确定有内容的接口（本人资料/配置/公告），
   解出来核对**字段数量与关键字段名**，对不上就是解码器错。
2. **两个接口互相对照**：列表接口应是 `{data:[...],total:N}`，单对象接口应是平铺 dict。
3. **未校准不得下阴性结论**：解码器烂着跑出的「0 命中」是**未测试**，不是「不存在」。

## 五、假阴性回扫（本卡最值钱的一步）

一旦发现解码器错了，**把所有建在它上面的历史结论重跑**：所有「0 命中 / 未发现 / 不存在」、
所有基于字段内容的枚举、上报给用户的数字口径（条数、命中率）。

实测 2026-10：某平台因「1 字节前缀」假设，135 条接口全量扫描报 0 明文，据此写了「服务端序列化层脱敏」；
换 offset 扫描重跑后，结论从「技术错误」变成「业务事实」——两者都算产出，但只有后者能写进报告。

## 六、坑

- **同一站不同接口包络可能不同**：有的直回明文 JSON，有的 AES，有的只包一层。按接口记录，别用一个解码器盖全站。
- **错误响应也包络**：`{"code":401,"data":"..."}` 里的 data 可能是加密的错误对象。
- **分页字段在外层**：`total`/`pageSize` 在外层，`data` 里才是数组，剥多了会丢分页。
- **脱敏在序列化层时,解码再完美也拿不到明文**:判据是**同一响应里 `showUsername`(全号)与 `username`(打码)并存**
  ⇒ 是业务脱敏,换攻击面(后台/代理后台/另一个客户端),不是换解码器。
- **双假阴性:头名错 + 扫密文,常同时存在**。只修解码器不够 —— 鉴权头若写成 `token:`(`Authorization:` 才对),
  探针根本进不了 handler,批量全 `401`。判据:登录 200 + JWT `exp` 未到 + 所有端点回同一个
  `401 INVALID_TOKEN`/`token异常` ⇒ 是**头名错,不是票错**。两闸同错时,修一道不够,旧结论必须整轮重跑。

## 支持文件

| 文件 | 内容 |
|------|------|
| `scripts/decode_envelope.py` | offset 扫描的通用解码器（单层/双层/前缀不定/gzip 自适应）+ 校准函数 |
| `references/sanbei-envelope-case.md` | 三北案：前缀长度 0/1/25/28 实录 + 假阴性回扫 + 多基址发现 |
