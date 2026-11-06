## 二、XPath语言基础

### 2.1 常用轴
```
/              根节点
//             任意深度
.              当前节点
..             父节点
@attr          属性
node()         任意节点
text()         文本节点
*              任意元素节点
@*             任意属性
ancestor::     祖先（可用于读上层数据）
parent::       父节点
child::        子节点
following-sibling::  后面的兄弟
preceding-sibling::  前面的兄弟
ancestor-or-self::   祖先及自身
```

### 2.2 运算符和函数（XPath 1.0/2.0）
```
and or not()    逻辑
= != < > <= >=  比较
+ - * div mod   算术
contains(), starts-with(), ends-with(), matches()(2.0)
substring(), string-length(), concat(), normalize-space()
translate()     字符串替换（1.0即可构造任意字符串）
count(), sum(), position(), last()
name(), local-name(), namespace-uri()
string(), number(), boolean()
doc(), doc-available()(2.0 文件/URL读取)
unparsed-text() (2.0 读取外部文本文件)
collection()    (2.0 集合访问)
true() false()  布尔
```

### 2.3 XPath 3.0/3.1 新特性与攻击价值（W3C Rec 2014/2017）
```
# 数据类型：maps 与 arrays（支持JSON数据模型）
map{'k': 'v'} 或 map:merge(...)      # map构造
[1, 2, 3]                            # array构造
? 查找运算符：$m?k、$arr?1、$arr?*  # 取值

# 新运算符
|| 字符串连接          # 'a' || 'b' → 'ab'
!  简单映射            # //user ! name(.)  不排序不去重
=> 箭头运算符（函数链） # $in => substring-before(' ') => upper-case()

# 高阶函数（first-class functions）
fn:for-each(seq, fn)、fn:filter(seq, fn)、fn:fold-left()、fn:fold-right()
function($x) { ... } 内联匿名函数；$f() 动态函数调用
# 数组函数：array:size() array:get() array:subarray() array:sort() ...

# 攻击价值
1. || 与 fn:codepoints-to-string() 构造被过滤的敏感字符串
2. 高阶函数 + 动态调用在过滤严格时提供替代写法
3. maps/arrays 是eXist/BaseX/MarkLogic等原生XML数据库的默认模型（见第七章）
```
**工程提示**：XPath 3.x 仅在 Saxon-HE、BaseX、eXist、MarkLogic、Altova 等实现中可用；大部分Web应用仍是1.0，Payload需按目标实现降级适配。

