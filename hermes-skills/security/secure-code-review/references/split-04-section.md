## 三、数据流追踪与污点分析

### 3.1 Source-Sink 模型深化

```
Source（输入源）:
- HTTP 参数（GET/POST/Header/Cookie/Path 参数）
- 文件上传内容、文件名
- 数据库查询结果（二次注入）
- 外部 API / 消息队列响应
- 环境变量 / 配置文件（若可被运维/攻击者控制）
- 反序列化对象字段

Sink（危险操作）:
- SQL 查询（直接/ORM 原生）
- 命令执行（系统调用/进程启动）
- 文件操作（读写/删除/移动）
- 反序列化（readObject/load/deserialize）
- 表达式解析（eval/parse/模板渲染）
- LDAP/XPath/GraphQL 查询
- HTTP 请求（SSRF）
- 日志（Log4j lookup / 敏感信息泄露）
- 响应输出（XSS/JSONP/CRLF 注入）

追踪路径:
Source → [Transform: 编码/截断/拼接/解密] → [Sanitize? 净化是否完备] → Sink
```

### 3.2 追踪路径与二次注入

```
1. 认证流程：Login → Token 验证 → 会话管理 → 权限检查
2. 授权流程：请求 → 权限校验 → 数据访问 → 响应过滤
3. 文件操作：上传路径 → 存储路径 → 访问路径 → 下载路径（改名/后缀/大小写）
4. API 链路：请求解析 → 参数验证 → 业务逻辑 → 数据操作
5. 二次注入：注入点入库 → 查询拼接 → 存储型 XSS/二次 SQL 注入
```

**二次注入审计要点：**
- 入库时的"过滤"（转义）在**读库再次拼接**时失效——审计`SELECT`结果进入第二个 Sink 的路径
- 存储型 XSS：写库不编码 + 读库输出不编码的双重缺陷
- 存储型命令注入：任务队列 payload 由 DB/Redis 驱动

### 3.3 手工数据流追踪技巧

```bash
# 1. 从 Sink 反向找 Source：grep 危险函数，回溯调用链
grep -rn "executeQuery\|exec\|pickle.loads\|readObject" --include="*.java" src/

# 2. 追踪同名变量传播：函数调用链
grep -rn "processUserInput\|handleData\|validateAndProcess" --include="*.java" src/

# 3. IDE 辅助：VS Code 安装安全审计插件（Semgrep/Snyk/CodeQL）逐跳追踪
#    使用 "查找所有引用" + 调用层级视图

# 4. 利用 AST 工具导出调用图
semgrep scan --config=auto --json src/ | jq '.results[] | {path: .path, start: .start.line, check_id: .check_id}'
```

### 3.4 工具化污点分析实战

**Semgrep 自定义污点规则（写自己的 taint-tracking 规则）：**
```yaml
# semgrep-rules/taint-sqli.yaml
rules:
  - id: taint-sqli-python
    mode: taint
    pattern-sources:
      - pattern: request.args.get(...)
      - pattern: request.form.get(...)
    pattern-sinks:
      - pattern: cursor.execute(...)
      - pattern: execute(f"...")
    message: "用户输入未净化进入 SQL 执行"
    languages: [python]
    severity: ERROR
```
```bash
semgrep scan --config=semgrep-rules/taint-sqli.yaml ./src
```

**CodeQL 污点追踪查询（Java SQL 注入）：**
```ql
import java
import semmle.code.java.dataflow.TaintTracking
import semmle.code.java.security.SqlInjection

from SqlInjectionSink sink, RemoteFlowSource source
where sink.getAUse().getEnclosingCallable().getFile().getName() = "UserDao.java"
  or source instanceof RemoteFlowSource
select sink, source, "SQL 注入污点路径"
```
```bash
codeql database create ./db --language=java --source-root=./src
codeql database analyze ./db --format=sarif-latest --output=result.sarif security-java.qls
```

