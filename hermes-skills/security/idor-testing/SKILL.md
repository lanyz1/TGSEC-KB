---
name: idor-testing
description: IDOR越权访问深度测试高级专业技能：水平/垂直越权/BOLA/BFLA、可预测标识符逆向(UUIDv1时间戳/熵分析/顺序ID)、多租户与跨租户SaaS隔离失效、LLM/AI平台对象越权(Langflow/Chainlit案例)、关系链IDOR、间接对象引用绕过、批量分配/原型污染、自动化BOLA检测方法论
version: 3.0.0
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='idor-testing', file_path='references/full.md')`

# IDOR越权访问深度测试高级技能

测绘引擎作业层先跑，下面长文当附录：

```bash
python3 tools/ops/idor_swap_probe.py --url 'https://授权/api/order?id=1' --ids 1,2 --case <案>
```

真源：`docs/playbooks/测绘引擎越权IDOR作业手法.md`。  
EQ 改 shop_id 阴性不算隔离。有身份先填对象矩阵。

<!-- split-index -->

## Section index

- [概述](references/split-01-section.md)
- [一、IDOR完整攻击面](references/split-02-idor.md)
- [二、检测方法](references/split-03-section.md)
- [三、绕过技术（高级）](references/split-04-section.md)
- [四、API特定IDOR](references/split-05-api-idor.md)
- [五、特殊场景（高级）](references/split-06-section.md)
- [六、可预测标识符深度分析（新增·高端）](references/split-07-section.md)
- [七、多租户与跨租户IDOR（新增·重点）](references/split-08-idor.md)
- [八、LLM/AI平台IDOR（新增·前沿）](references/split-09-llm-ai-idor.md)
- [九、自动化BOLA检测方法论（新增·实战落地）](references/split-10-bola.md)
- [十、自动化工具](references/split-11-section.md)
- [十一、IDOR测试清单（高级版）](references/split-12-idor.md)
- [十二、修复建议（高级）](references/split-13-section.md)
- [注意事项](references/split-14-section.md)
- [SRC 猎手补充手法](references/split-15-src.md)
- [真源](references/split-16-section.md)
- [1. 先分类鉴权中间件(看报错格式,一票定族)](references/split-17-1.md)
- [2. IDOR 批量测试要点](references/split-18-2-idor.md)
- [3. 业务归属校验陷阱(最难发现也最值钱 = PII 明文出口)](references/split-19-3-pii.md)
- [4. 枚举资源 id:参数名陷阱 + 下架资源](references/split-20-4-id.md)
- [5. nginx 403 ≠ 接口不可达(路径级访问控制绕过)](references/split-21-5-nginx-403.md)
- [6. 前端构建泄露 → 新旧版本 diff](references/split-22-6-diff.md)
- [7. 多机全库拉取编排(跳板机/云主机)](references/split-23-7.md)
- [取证与报告](references/split-24-section.md)
- [References / 实战案例](references/split-25-references.md)
- [补充：用户列表 IDOR → 密码重置 Token 收割链（2026-09-16）](references/split-26-idor-token-2026-09-16.md)
- [2026-10 情报批增量（数组包裹 → ORM 批量越权，Node 系）](references/split-27-2026-10-orm-node.md)
