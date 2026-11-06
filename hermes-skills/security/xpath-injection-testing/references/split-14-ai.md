## 十三、AI大模型结合

### 13.1 AI辅助生成XPath payload
```
# 示例提示词（注入点上下文→payload）
"目标XPath查询: //user[username='%s' and password='%s']（Java XPathFactory，XPath 1.0）。
 请生成：1)认证绕过payload 2)布尔盲注提取password的payload 3)WAF存在时（拦截'or'与'1=1'）的等价绕过。输出可直接提交的表单值。"

# 示例提示词（盲注脚本生成）
"基于布尔盲注，目标判定特征为'Login success'关键字，提取//user[1]/secret。
 用Python生成：二分长度+字符集二分+8线程并发的提取脚本（requests库），
 注意引号转义与payload闭合为 x' or (cond) or 'x'='。"
```
**价值**：LLM可批量生成多形态等价表达式（translate/codepoints-to-string/嵌套函数）用于绕过特征WAF，并自动生成针对不同语言后端（lxml/XPathFactory/DOMXPath）的适配payload。

### 13.2 LLM审计XPath拼接代码（防侧）
```
# 提示词：对代码做CWE-643审计
"审计以下代码中所有XPath查询构造点，标记：1)用户输入是否直接拼接进查询字符串
 2)是否使用参数化/变量绑定 3)引号是否转义 4)给出修复代码。代码: ..."
```
**审计规则（LLM应遵循）**：任何`f"//...{input}..."`、`"...'"+input+"'..."`、`sprintf("//%s")`进XPath求值函数=信号；优先推荐变量绑定（lxml `$var`、Java `XPathVariableResolver`、XQuery `declare variable external`）。

### 13.3 AI驱动自动化检测
- **语义差异判定**：用LLM替代正则判断真假响应差异（正文变化/状态码/长度变化），提高盲注oracle鲁棒性
- **自适应payload生成**：根据WAF拦截响应自动迭代生成绕过变体（Agent式循环：发送→判断拦截→变形→重发）
- **文档结构推断**：喂入部分枚举结果，让LLM推断XML schema并预测敏感节点路径（大幅缩短第四章结构枚举）
- **多目标并行**：AI编排注入测试矩阵（引号/双引号/数字上下文/属性上下文）并汇总结果

### 13.4 注意事项
- **验证优先**：LLM生成的payload必须实际验证，防止幻觉语法（如XPath中误用SQL注释`/**/`、`--`）
- **版本对齐**：提示词中明确XPath版本与后端库，避免生成3.x特性用于1.0实现
- **合规约束**：AI生成的自动化工具同样仅限授权范围；在提示词与脚本中固化授权标记与限速参数

