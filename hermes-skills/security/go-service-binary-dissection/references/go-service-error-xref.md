# Go 服务端二进制解剖配方:错误串 xref / 字符串还原 / 中间件样例

配套 SKILL.md 的完整可复制配方。适用:未剥离 Go 服务二进制(后端服务类)。

## 0. 验证 load delta(文件偏移 ↔ VA)

Go ELF 常见 `VA = 文件偏移 + 0x400000`。**先验证再信**:取符号表里带 VA 的函数,算 `off = VA - 0x400000`,读该处首字节与 `objdump -d` 首字节比对;或用 `strings -t x` 偏移交叉核对。多段各自换算(`objdump -h` 给 VMA/offset)。

## 1. 错误串 → 函数(xref 扫描)

```python
import struct
data = open(BIN, "rb").read(); delta = 0x400000
off = data.find("错误串".encode()); va = off + delta
hits = []
for i in range(len(data) - 7):
    if data[i] not in (0x48, 0x4c): continue      # REX.W(±R)
    if data[i+1] != 0x8d: continue                # lea
    if (data[i+2] & 0xc7) != 0x05: continue       # mod=00,rm=101 ⟹ [rip+disp32]
    disp = struct.unpack_from("<i", data, i+3)[0]
    if i + 7 + disp + delta == va: hits.append(i + delta)   # 命中指令 VA
```

- 命中 VA → 函数映射:`sym_all.txt` 取 `F .text` 行(addr,size,name)按地址排序 + `bisect_right` 找包含地址的函数。
- 同一句文案可能有第二份拷贝,`find` 只给首个;`re.finditer(re.escape(s), data)` 拿全部位置分别查。
- LEA 覆盖 Go 绝大多数字符串装载;经栈转手的引用漏网时,在候选函数反汇编里手工看。

## 2. 反汇编 + 注释法读函数(lea 串 → 文本)

```bash
objdump -d -M intel --start-address=0x.. --stop-address=0x.. <bin> > f.txt
```

```python
import re
for m in re.finditer(r"# ([0-9a-f]+) ", txt):
    va = int(m.group(1), 16); off = va - delta
    chunk = data[off:off + 160]; end = chunk.find(b"\x00")
    try: print(chunk[:end].decode("utf-8"))
    except Exception: pass
```

- 只取落在字符串区段的引用;`type:*`/`itab` 类是类型元数据,跳过。
- `grep -E "call|lea"` 或全部 `call <sym>` 去重排序 = 函数故事;见 `gins.Redis` / `Dao...Where/Scan` / keyfunc(`*.func1`)即可判定校验分层。

## 3. 中间件解剖样例(Go/Gin + GF 栈)

JWT 中间件典型分层(顺序读 = 校验顺序):

```text
ParseWithClaims(jwt/v5) → keyfunc(*.func1)取全局密钥 → 错误分支(解析失败 / 已失效)
→ Redis 查询(登记簿/黑名单/禁用) → 用户表/应用表查询 → 客户端 IP 检查 → SetCtxVar
```

- keyfunc 读的是编译期全局(如 `utility.JwtKey`):密钥/配置真源 = **写该全局的 init**,不是 read 点;下一步找写入方拿配置键名。
- 中间件内含 Redis/DAO 调用 = 服务端有状态校验,与黑盒「真钥=错钥同句」差分结论互证。
- 每个错误串引用点 = 一个分支;错误文案对分支条件(比较 exp / Redis 值 / 表行数)逐一对上,别靠文案猜层次。

## 4. 纪律

- 几十 MB 二进制上的扫描/解析脚本落盘跑、结果落文件。
- 别停在「列出符号」:xref + 分支阅读才是读出服务端逻辑的动作。

## 5. 无代码 xref → 数据段指针链(切片字面量/路由表/白名单)

症状:目标串 grep `# <VA>` 与字节扫 lea **都空**。原因:串被 `[]string{...}` 等**数据段字面量**消费,没有任何指令直接 lea 它。反着走两跳:

1. **string-header 表**:扫该串 VA 的 LE64(`scripts/find_ptr_refs.py <bin> <delta> <VA>`)→ 命中 = 数据段 `{ptr LE64, len LE64}` 表条目(16B/条);len 与串长复核。
2. **看全表**:同表邻居 = 同类串(路由表往往几十条路径一屏打全);记表基址。
3. **slice 描述符**:再扫**表基址 VA** 的 LE64 → 命中 = `{ptr,len,cap}` 描述符槽(24B),len = 条目数。
4. **拿变量名**:GNU 全量 dump 里 grep 描述符或表地址(`# <addr>`)→ 注释直接解析出**符号名**(如 `wallet/pkg/white.AuthWhiteApis`)——拿变量语义的捷径,别手工猜表用途。
5. **消费函数**:grep 描述符 VA 的代码引用(或 symtab 最近符号)→ 读上下文定「谁在何时查这张表」。

语义红利:名单变量名 + 消费点直接回答「为什么某请求绕过某中间件」——路由在 `AuthWhiteApis`(消费点落在 JWT 中间件区)= 跳过 JWT,无票请求仍达后续层。gf 服务常以独立 `pkg/white` 包放多张名单(`AuthWhiteApis`/`PublicWhiteApis`/`SecretWhiteApis`/`Decrypt`),整包符号枚举一次拿全。

## 6. GoFrame 服务 403/报错判层速查

- **信封判层**:应用响应 = `{"ErrCode":N,"ErrMsg":"...","ResData":null}`;不存在路由 → `{"ErrCode":65,"ErrMsg":"Not Found"}`(应用自身兜底)。拿不存在路由当对照:同型信封 + `trace-id` 头 = 应用内响应;CF/WAF 自产页(HTML/特征串)另判。
- **状态码映射**:`response.MiddlewareHandlerResponse` = ErrCode→HTTP 状态处(找 `cmp $0x193,%rdx` 类)。
- **框架 403 噪声**:`$0x193` 立即数命中 gf `ghttp.(*Response).WriteStatus`(BasicAuth/静态文件分支)= 框架内部,直接排除。
- **i18n**:`middleware/i18n.T` 调用形态 `LEAQ key(IP), CX; MOVL $len, DI; CALL i18n.T`,键从 lea 目标解析;翻译资源运行时磁盘载入(`manifest/i18n`,不内嵌),响应文案与二进制对不上先想这里。
- **签名中间件读全**:读到**放行出口**(如 `err==nil && ok ⇒ return true`)为止;活体证明「已过某层」须由落点层变化(新错误后缀/新错误体)支撑,不只靠「没了 401」。