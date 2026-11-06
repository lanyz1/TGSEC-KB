# 案例课：Coruna 水坑按 iOS 版本分发 Stage —— 从投递端 JS 反推支持矩阵

> 来源：同行作业机样本（2026-10）· 域：reverse-engineering / 移动投递链
> 原文与凭据不入库；本文只留可复用手法。

## 一句话

Coruna 系水坑页把「iOS 版本 → Stage1/Stage2 载荷」的映射**写在前端 JS 里**；拿到 `platform_module.js` 就能离线还原它支持哪些版本、投什么载荷，不需要真机也不需要跑链。

## 前提 / 指纹

- 水坑页有按 UA 版本分支的 JS（搜 `navigator.userAgent` + `match(/OS (\d+)_/)`）
- 同目录常见：`platform_module.js`（上报/选型）、`server_updated.py`（投递端）、`server_original_backup.py`
- 载荷命名固定：`bluebird.js` / `terrorbird.js` / `cassowary.js` / `seedbell.js` / `seedbell_pre.js` / `Stage3_CardStealer_Loader.js`

## 链

```text
水坑页 JS 里取版本分支表（UA → stage 文件）
→ 校 server_updated.py 的下发条件（UA 白名单 / 地区 / 时间窗）
→ 得到「版本 → Stage1/Stage2 → Stage3 CardStealer」完整矩阵
→ 只做识别与归因：命中设备可判定其会被投哪一档
```

- 实测矩阵（同行 kit 文件结构）：

| iOS 版本 | Stage1 | Stage2 |
|---|---|---|
| 15.6 – 16.1.2 | `bluebird.js` | — |
| 16.2 – 16.5.1 | `terrorbird.js` | — |
| 16.3 – 16.5.1 | — | `seedbell.js` |
| 16.6 – 16.7.12 | — | `seedbell.js` |
| 16.6 – 17.2.1 | `cassowary.js` | `seedbell_pre.js` |

- 第三阶段统一 `Stage3_CardStealer_Loader.js`，落地后由 `platform_module.js` 上报回 C2

## 判据与边界

- 命中判据：JS 里存在版本区间 + stage 文件名的映射表，且投递端按同一区间下发
- 失败边界：
  - 页面用服务端 UA 判定（JS 里看不到表）→ 只能从投递端源码/log 反推
  - 混淆过的版本比较（数字拆分/编码）→ 断点或 AST 还原比较表达式再取区间
  - 版本区间有重叠（如上表 16.3–16.5.1 同时命中 terrorbird 与 seedbell）→ 以投递端 `if/else` 的实际顺序为准，别按区间猜
- 同族变体：Android 水坑按 `Build.VERSION` / 厂商分支；桌面按 Chrome 大版本分发不同 V8 exploit——判据都是「分支表在投递端而不是载荷里」

## 检查清单

- [ ] 先取 `platform_module.js` 与投递端 py，别急着分析载荷本体
- [ ] 记录 UA 判定用的是 `OS x_y` 还是 `Version/x.y`（Safari 与 App 内 WebView 口径不同）
- [ ] 分支表按实际代码顺序抄，不用区间并集
- [ ] 只用于识别/归因；不构造投递、不复用载荷
- [ ] 样本哈希与路径写进案卷，原文不入库
