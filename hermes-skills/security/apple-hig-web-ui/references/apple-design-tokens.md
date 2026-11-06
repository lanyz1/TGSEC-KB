# Apple HIG 设计令牌(A2 纯白极简 · 用户定稿)

本用户最终选定的配色方向(2026-07 会话定稿),后续 Apple 风项目可直接照抄,微调即可。

## A2 纯白极简 · :root 令牌

```css
:root{
  --nav-bg:#F9F9F9; --nav-ink:#6E6E73; --nav-ink-active:#1D1D1F;
  --nav-item-hover:rgba(0,0,0,.05); --nav-item-active:rgba(0,0,0,.07); --nav-border:rgba(0,0,0,.08);
  --bg:#FFFFFF; --surface:#FFFFFF;
  --border:#E8E8ED; --border-strong:#D4D4D9;
  --ink:#1D1D1F; --muted:#6E6E73; --faint:#98989F;
  --brand:#000000; --brand-ink:#1D1D1F; --brand-soft:rgba(0,0,0,.05);
  --link:#0071E3;                 /* Apple 蓝,仅链接/点缀 */
  --g:#34C759; --gs:rgba(52,199,89,.12);
  --blue:#007AFF; --blue-soft:rgba(0,122,255,.1);
  --orange:#FF9500; --orange-soft:rgba(255,149,0,.12);
  --amber:#FF9500; --amber-soft:rgba(255,149,0,.12);
  --red:#FF3B30; --red-soft:rgba(255,59,48,.1);
  --gray-soft:#F2F2F4; --gray-ink:#6E6E73;
  --mono:ui-monospace,SFMono-Regular,"Cascadia Mono",Consolas,monospace;
  --r-lg:16px; --r-md:10px; --r-sm:8px;
  --shadow:0 1px 2px rgba(29,29,31,.03);
}
```

## 关键规则
- **主按钮 = 纯黑** `#000`(hover `#2E2E30`),**胶囊** border-radius:999px;危险按钮红字 `#D70015` + 浅红底
- 徽章 = 系统色 10-15% 透明度底 + 深色文字:绿底字 `#248A3D`、蓝底字 `#0A60C0`、橙底字 `#B25A00`、红底字 `#D70015`、灰底字 `#6E6E73`;胶囊
- 侧边栏浅灰 `#F9F9F9`,选中项 = `rgba(0,0,0,.07)` 底 + 黑粗体,**无左色条**(Apple 用背景区分)
- 图表:黑线 `#1D1D1F` 2px + 黑色面积渐变(0.10-0.14 → 0),对比线灰色虚线 `#C9C9CE`,网格 `#F0F0F2`
- 表格表头浅灰 `#FAFAFC`,行 hover `#FAFAFC`,细分割线 `#E8E8ED`
- 排序箭头 ▲▼ 小字加在表头文字后

## Apple 系统色对照(状态语义)
| 语义 | 色值 | 浅底 |
|---|---|---|
| 正常/成功 | #34C759 | rgba(52,199,89,.12) |
| 信息/待发货 | #007AFF | rgba(0,122,255,.1) |
| 警告/售后 | #FF9500 | rgba(255,149,0,.12) |
| 错误/驳回 | #FF3B30 | rgba(255,59,48,.1) |
| 中性/停用 | #8E8E93 | rgba(142,142,147,.12) |

## 登录页(Apple 风)
- 品牌区 = 纯黑底白字,logo 方块白底黑字,slogan 强调用 `#0071E3`;表单区白底
- 卖点条目:白 9% 底圆角方块图标(蓝描边)+ 白粗体标题 + `#98989F` 说明

## 否决过的风格(用户原话反馈)
- 科技风:发光/渐变/网格线 → "AI 味道太重"
- 传统深色侧栏 + 浅内容 SaaS → "太老套"
- TikTok 黑粉(侧栏纯黑 + 粉 #FE2C55)→ "不满意"
