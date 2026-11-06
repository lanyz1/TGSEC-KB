## 十五、修复建议

### 15.1 输出编码（核心修复，按上下文）
| 上下文 | 编码方式 | 示例 |
|-------|---------|------|
| HTML标签之间 | HTML实体编码 | `&lt;&gt;&amp;&quot;&#x27;` |
| HTML属性值 | 属性编码+引号转义 | `&quot;` + 引号实体 |
| JavaScript上下文 | JS字符串转义（`\x`/`\u`） | 绝不可只做HTML编码 |
| URL上下文 | URL编码+协议白名单 | 仅允许http/https/mailto/# |
| CSS上下文 | CSS转义+禁用url(javascript:) | CSS上下文XSS极少见但危险 |

**正确姿势**：优先使用框架的上下文感知编码（React JSX/Vue插值默认已编码），手动拼接场景用OWASP ESAPI/encodeURIComponent等专用库。

### 15.2 CSP配置（严格基线）
```http
# 无内联、无eval、nonce/hash白名单
Content-Security-Policy: default-src 'none'; script-src 'nonce-随机值'; 
  style-src 'self'; img-src 'self' data:; base-uri 'none'; 
  object-src 'none'; frame-ancestors 'none'; form-action 'self';
# 配合Trusted Types
Content-Security-Policy: require-trusted-types-for 'script'; trusted-types 策略名;
```
- **必须配置**：`base-uri 'none'`（防劫持相对路径）、`object-src 'none'`（防插件XSS）
- **禁止**：`'unsafe-inline'`/`'unsafe-eval'`/`data:` script、裸通配符`*`
- **strict-dynamic需审计gadget**：即使strict-dynamic也有13/16框架被gadget绕过
- **nonce不落地DOM**：nonce不能出现在HTML属性中可被读取的位置（DOM XSS可读nonce）

### 15.3 Trusted Types部署
```javascript
// 启用后所有危险sink强制Trusted对象
if (window.trustedTypes && trustedTypes.createPolicy) {
  const policy = trustedTypes.createPolicy('app', {
    createHTML: (s) => DOMPurify.sanitize(s),
    createScriptURL: (u) => (new URL(u, location.origin).origin === location.origin ? u : 'about:blank')
  });
}
// 上报违规而非直接拦截（灰度）
// 通过report-to/报告端点收集TT违规，逐步收敛
```
**注意**：策略实现本身必须安全（createHTML内必须消毒，createScriptURL必须校验来源），否则等于自挖绕过口（MutantBedrog类攻击即滥用宽松策略）。

### 15.4 消毒器使用规范
- **同一上下文消毒**：`sanitize()`输出只用于innerHTML插入；禁止拼入模板/script.text/属性/svgElement
- **消毒后再验证**：消毒→序列化→再解析→检查活动节点（防御mXSS类）
- **固定最新版本**：DOMPurify持续修复mXSS（2024-2026年10+个CVE），版本锁定在旧版=留后门
- **警惕自定义配置放宽**：`ALLOWED_TAGS`/`CUSTOM_ELEMENT_HANDLING`/`IN_PLACE` 均产生历史绕过面

### 15.5 框架与库安全
- 避免`dangerouslySetInnerHTML`/`v-html`/`{@html}`/`bypassSecurityTrustAs*`，必须用时前置消毒+URL协议白名单
- 不使用用户可控模板编译（Vue template/Angular动态组件）
- SSR/Hydration JSON序列化使用安全库（防`</script>`逃逸）
- 及时升级：jQuery≥3.5（CVE-2020-11022/11023）、Vue 3（Vue 2已EOL，CVE-2024-6783）、Bootstrap≥4（CVE-2025-1647）
- npm audit/Snyk定期检查前端供应链

### 15.6 Cookie与会话安全
- HttpOnly + Secure + SameSite=Strict（或Lax）
- 敏感操作二次验证（密码/OTP），降低ATO风险
- 即使Cookie安全，XSS仍可CSRF/读取页面——会话安全不能替代输出编码

### 15.7 纵深防御组合拳（按优先级）
1. **上下文感知输出编码**（消除根因）
2. **严格CSP + Trusted Types**（纵深阻断）
3. **HttpOnly/SameSite Cookie**（减轻会话风险）
4. **WAF语义分析**（不依赖签名，用语义/解析一致性检测）
5. **CSP report-only + TT违规上报**（持续监测绕过）
6. **AI驱动的WAF规则自动更新**（对抗AI生成payload，GenXSS模式）

