---
name: information-gathering
description: 信息收集深度渗透测试专业技能（v3.0 高级版）：被动侦察全维度（证书透明度CT新来源/DNS历史/泄露数据库/暗网社工数据）、主动侦察与隐蔽性（代理池/指纹伪装/低频扫描）、子域名接管检测与利用、云资产发现（对象存储/云函数/未绑定域名）、小程序与App移动端资产、关联信息图谱（员工/组织架构/供应链）、AI大模型辅助OSINT自动化、信息收集到攻击面优先级评估的决策方法论
version: 3.0.0
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='information-gathering', file_path='references/full.md')`

# 信息收集深度测试技能（高级版）

<!-- split-index -->

## Section index

- [概述](references/split-01-section.md)
- [一、信息收集方法论](references/split-02-section.md)
- [二、被动侦察全维度（OSINT·企业/人员/泄露）](references/split-03-osint.md)
- [三、证书透明度（CT）与 DNS 历史](references/split-04-ct-dns.md)
- [四、子域名枚举（被动+主动全维度）](references/split-05-section.md)
- [五、子域名接管检测与利用](references/split-06-section.md)
- [六、主动侦察与隐蔽性](references/split-07-section.md)
- [七、Web 指纹与内容识别](references/split-08-web.md)
- [八、WAF/CDN 识别与真实 IP 溯源](references/split-09-waf-cdn-ip.md)
- [九、云资产发现](references/split-10-section.md)
- [十、移动端资产（小程序/App）](references/split-11-app.md)
- [十一、关联信息图谱：员工/组织/供应链](references/split-12-section.md)
- [十二、泄露数据库与暗网情报](references/split-13-section.md)
- [十三、AI 大模型结合](references/split-14-ai.md)
- [十四、信息收集 → 攻击面优先级评估决策方法论](references/split-15-section.md)
- [十五、工具链总表](references/split-16-section.md)
- [十六、信息收集检查清单](references/split-17-section.md)
- [十七、修复建议](references/split-18-section.md)
- [十八、注意事项](references/split-19-section.md)
- [真源](references/split-20-section.md)
- [触发条件](references/split-21-section.md)
- [1. 被动枚举(不发 DNS 请求)](references/split-22-1-dns.md)
- [2. 主动 DNS 爆破](references/split-23-2-dns.md)
- [3. DNS 历史与旁站](references/split-24-3-dns.md)
- [4. 存活探测与指纹](references/split-25-4.md)
- [5. DNS 接管检测(Subdomain Takeover)](references/split-26-5-dns-subdomain-takeover.md)
- [6. 完整流程串联(一键)](references/split-27-6.md)
- [Pitfalls](references/split-28-pitfalls.md)
