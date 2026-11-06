---
name: ssrf-testing
description: SSRF服务器端请求伪造深度测试技能：内网渗透全协议攻击面、云元数据、Gopher/Dict全协议利用、WAF绕过、Redis/FastCGI/Memcached RCE利用链
version: 2.0.0
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='ssrf-testing', file_path='references/full.md')`

# SSRF服务器端请求伪造深度测试技能

测绘引擎作业层先跑，下面长文当附录：

```bash
python3 tools/ops/ssrf_probe.py scan --base https://授权站 --case <案>
```

真源：`docs/playbooks/测绘引擎SSRF作业手法.md` · 云链 `云元数据SSRF利用链手法.md`。  
IMDSv2 纯 GET 常 405，换能带头的 SSRF。元数据 IP 不扩进 targets。

<!-- split-index -->

## Section index

- [概述](references/split-01-section.md)
- [一、SSRF完整攻击面](references/split-02-ssrf.md)
- [二、SSRF检测与分类](references/split-03-ssrf.md)
- [三、IP与URL绕过技术](references/split-04-ip-url.md)
- [四、云元数据攻击](references/split-05-section.md)
- [五、协议级高级利用](references/split-06-section.md)
- [六、内网Web攻击利用](references/split-07-web.md)
- [七、Blind SSRF利用](references/split-08-blind-ssrf.md)
- [八、WAF绕过与高级技巧](references/split-09-waf.md)
- [九、工具链](references/split-10-section.md)
- [十、SSRF测试清单](references/split-11-ssrf.md)
- [十一、修复建议](references/split-12-section.md)
- [注意事项](references/split-13-section.md)
- [真源](references/split-14-section.md)
- [SSRF 防护绕过 — deny-list/IP 校验必漏地址库(2026-09 增量)](references/split-15-ssrf-deny-list-ip-2026-09.md)
- [SSRF 内网打点速查(老路径,常用)](references/split-16-ssrf.md)
