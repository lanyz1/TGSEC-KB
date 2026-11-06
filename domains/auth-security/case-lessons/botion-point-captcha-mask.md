# 案例课：botion 点选验证码 —— 遮罩吃事件、序号才是成功判据

> 来源：报告包 cont233/乐竞（2026-10）· 域：auth-security / 注册自动化

## 一句话

点不中不是坐标问题，是 `botion_box_layer`/`botion_box_btn` 遮罩吃了鼠标事件；先 `pointer-events:none`，再点 `botion_bg`。成功判据是 tip 下出现序号 `1/2/3`，不是变色也不是文案。

## 链

1. 打开注册页，等 `botion_*` DOM 就绪
2. `document.querySelectorAll('.botion_box_layer,.botion_box_btn').forEach(e=>e.style.pointerEvents='none')`
3. 点 `botion_bg` 上的目标坐标（背景图坐标 → 页面坐标换算）
4. 每点一次检查 tip 下是否新增序号 `1/2/3`
5. 三目标全过 → 点「确定」（中文文案，不是 OK）
6. 换题必须 JS 点 `[class*=botion_refresh]`，裸 mouse 常不换

## 判据

- `iou>=0.55` 三目标全过 + 新 `bgUrl` 才点确定
- 密码预言机：`entryErr=22411` + 验证错误 = **密码对、卡二次验证**；`22001` = 账密错
- 注册 captchaId 常出 icon，登录 captchaId 常出 word，同一风控会切换

## 边界

- 上游 `:8099 load/verify` 403 → 改走 JSONP load 域或 CDP Fetch 代理
- 离线 chamfer 0.85–0.95 仍可能中心偏，必须在线校验
- 别把「点了没反应」当验证码失败，先查 pointer-events

## 检查清单

- [ ] 遮罩 pointer-events
- [ ] 序号判据
- [ ] refresh 用 JS click
- [ ] 确定按钮中文
- [ ] entryErr 语义

---
@TGSEC社区 · @TGSEC-Qtzuu 整理
