---
name: cloud-waf-rule-bypass
description: "Use when 云 WAF 拦截页/403 挡住目标. Host 行归一化绕过规则集."
---

# 云 WAF 规则集绕过

目标须在授权范围。本库已有专卡(`401-403-bypass-techniques`、`edgeone-origin-bypass`)时按那里的方法论走;
本卡专管它们没写透的那一步:**云 WAF 按精确 Host 字符串绑定规则集**,以及打不通时怎么判自己走错了方向。

<!-- split-index -->

## Section index

- [0. 先给响应分类,不要只看状态码](references/split-01-0.md)
- [1. ★ 先判 WAF 在哪一层——它决定你打源站还是打规则集](references/split-02-1-waf.md)
- [2. ★ 主招:Host 行归一化(一次绕过整层规则)](references/split-03-2-host.md)
- [3. 配套:路径关键词单字符编码](references/split-04-3.md)
- [3b. ★ 第二层:200 + JS 质询页(反机器人层)——别用 §2/§3 打](references/split-05-3b-200-js-2-3.md)
- [4. 绕过成立后立刻回头重打旧拦截面](references/split-06-4.md)
- [5. 纪律与坑](references/split-07-5.md)
- [6. ★ 修正：POST 通道存在于「分号后缀」形式（2026-09 实测，推翻 §3b 的旧结论）](references/split-08-6-post-2026-09-3b.md)
- [7. 分号/后缀通道对非 Spring 栈是读取通道](references/split-09-7-spring.md)
- [参考](references/split-10-section.md)
