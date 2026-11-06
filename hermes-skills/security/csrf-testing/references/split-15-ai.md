## 十三、AI大模型结合攻防

### 13.1 AI辅助生成CSRF PoC页面
```
把Burp捕获的原始请求（方法/URL/Headers/Body）交给LLM，要求输出可直接保存为HTML的PoC：
Prompt模板：
"下面是从目标站点捕获的CSRF敏感请求，请生成一个可直接在浏览器打开的HTML PoC文件，
要求：1) 自动提交表单 2) 保留全部参数与Cookie行为 3) 若Content-Type为application/json，
尝试enctype=text/plain拼JSON方案 4) 同时生成GET载体（img/link）版本 5) 给出多浏览器（Chrome/Firefox）
与SameSite Lax/Strict的预期差异说明。请求如下：[粘贴原始请求]"

LLM可自动完成的变体生成：
- 方法覆盖（_method=DELETE/PUT）
- text/plain JSON 拼接（input name/value 边界技巧）
- no-referrer meta / sandbox iframe / data: URL 变体
- 多步表单串联（iframe target链式提交）
- OAuth callback 构造（code/state/redirect_uri参数篡改）
```
**注意：** LLM生成的PoC必须人工核对后再测试——LLM可能遗漏Cookie Domain细节或生成错误边界拼接。

### 13.2 LLM审计Token校验逻辑
```
把服务端Token校验代码（Synchronizer/Double Submit/HMAC/中间件）交给LLM做代码审计：
Prompt模板：
"以下是CSRF Token校验实现代码，请以红队视角审计：
1) Token是否仅校验存在性/长度/格式而非值？
2) Token是否绑定Session与User？
3) 校验是否仅针对特定HTTP方法/Content-Type（可被方法覆盖/换Content-Type绕过）？
4) 双提交实现中Cookie是否可被注入/覆盖（Domain/Path/前缀缺失）？
5) HMAC实现是否存在长度扩展/算法混淆/时序漏洞？
6) 是否存在校验顺序缺陷（先执行操作后校验）？
请逐条给出'可利用/不可利用/需进一步验证'结论与对应PoC思路。
代码：[粘贴代码]"

适用场景：
- 逆向JS前端Token生成逻辑（Angular/Django/Rails/Spring Security）
- 审计中间件顺序（Token校验在鉴权前还是后）
- 识别"全局开关/测试模式"后门校验分支
```

### 13.3 AI驱动CSRF检测扫描
```
现代工具链（2025-2026）：
- Strix（开源，~24k stars）：多AI代理协作，浏览器自动化测试XSS/CSRF等客户端漏洞，
  自动生成PoC并在Docker沙箱验证（无假阳性）
  pip install strix-agent; strix --target https://target.com
- XBOW（商业）：HackerOne全球榜首，数千并发代理自动攻击Web应用，发现大量0day
- Shannon（开源，Claude Agent SDK）：白盒+黑盒混合，源码驱动攻击策略，自动验证
- Burp+LLM插件：捕获请求→LLM生成PoC→人工复核（红队标配工作流）

AI扫描自动化流程（建议）：
1. 爬取应用，识别全部状态改变接口（方法/参数/是否带Token）
2. 对每个接口生成"无Token/空Token/复用Token/换用户Token/换方法"测试矩阵
3. 结合SameSite/Cookie审计结果自动选择绕过策略（Lax窗口/方法覆盖/双提交注入）
4. LLM分析服务端响应差异（403 vs 200）判断校验逻辑
5. 输出PoC + 人工复核 + 沙箱验证
局限（arXiv 2510.14700实证）：LLM agent在"认证障碍/复杂环境"下成功率大幅下降（>33.3%），
复杂业务流仍需人工，AI产出必须人工兜底
```

### 13.4 AI在防御侧的反制（攻防视角）
```
- 目标若使用LLM/AI Agent处理请求（自动化客服/操作机器人），其"会话"往往非Cookie而是
  API Token/对话ID → SameSite完全失效，CSRF演变为"诱导AI执行操作"（prompt注入联动）
- 目标若用LLM审查请求（WAF-AI），可通过语义混淆（编码/分块/多步诱导）绕过LLM理解
- 检测自身PoC是否被AI-WAF拦截时，可用LLM生成混淆变体批量对比
```

