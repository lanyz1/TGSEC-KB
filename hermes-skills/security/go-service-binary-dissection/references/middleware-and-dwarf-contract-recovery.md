# 中间件语义与请求契约的 DWARF 反查(带调试信息的 Go 服务)

适用:`strings` 已经把路由表/字段名/校验文案榨过一遍(见 `route-surface-and-contract-extraction.md`),
剩下的问题是**「谁读了哪个头/哪个参数、查了哪张表、按什么顺序」** —— 即中间件语义与 struct↔表映射。
二进制**未被 strip 调试信息**时,这一步可以一次拿全,不必靠黑盒矩阵试探。

前置判断:DWARF 在不在(Go 默认编译带 `debug_info`;镜像版/加壳版可能没有)。
不带 Go 工具链也能做:用 `pyelftools` 读 DWARF/capstone 反汇编即可,不需要 `go tool`/`objdump`。

## 1. DWARF 直读结构体/中间件/DAO(一次拿到「有几道闸、各叫什么」)

```python
from elftools.elf.elffile import ELFFile
f = open(binpath,'rb'); elf = ELFFile(f); dw = elf.get_dwarf_info()
want = ('ThirdParty', 'Sign', 'Limit')          # 按业务词过滤,别全量打印
for cu in dw.iter_CUs():
    for die in cu.iter_DIEs():
        n = die.attributes.get('DW_AT_name')
        if n and any(w.lower() in n.value.lower() for w in want):
            print(die.tag, n.value, die.offset)
```

- `DW_TAG_subprogram` 命中 = **函数级**(中间件/逻辑函数);`DW_TAG_structure_type` = 结构体;
  两者一起出 `middleware/signature.XxxSignVerification` + `middleware/third_party.XxxLimit` + `XxxApps` 实体/DAO 时,
  **闸门的数量、包路径、职责分工**就齐了 —— 比黑盒猜参数族快一个数量级。
- **实体 + DAO 名 → 表名**:GoFrame 的 `entity.Xxx` 配 `dao.XxxDao`,表名回 `strings` 里取 `orm:"<表名>"`
  或 DAO 的 `Table()` 常量 ⇒ **闸门判定所查的表名是硬证据**(例如某中间件的 `...Dao.Where().Where().Scan()`
  后报「api_key不存在」⇒ 平台身份由该表的 `api_key` 列识别)。
- 中间件**读哪些头/参数**,在函数体反汇编里逐条读出来(下一节);DWARF 只告诉你「是哪几个函数」。

## 2. 逐函数反汇编:头名 / 参数名 / 表名 / 错误码的顺序就是执行顺序

从 symtab 或 DWARF 拿 `st_value`(起址)与 `st_size`(长度),**只解码这一段**,
按地址序收集两类东西:

1. `RIP` 相对内存操作数 → 解析出地址 → 落在字符串区就还原成字符串。
   **Go 字符串常量是 `{ptr,len}` 头**:操作数给的是**头地址**,要再读 ptr+len 才是正文;
   直接把操作数当地址去读会得到乱码并误判「读不到」。
2. `call` 立即数 → 映射到最近的符号名。**被调用的中间件/解析函数名 = 该处的语义**
   (如 `json.Unmarshal` / `GetQueryMap` / `time.Now`/`After`/`Add` / `Dao...Scan()`)。

按地址序读一遍,就是一个中间件的**完整判决流程**:先取哪个头、再取哪个查询串参数、
查哪张表、命中后干什么、未命中报哪句文案 → 参数族与顺序一次定死。

## 3. 硬坑(实测代价最高)

- **别用「整节线性扫描 + skipdata」当 xref 的判据**。在几十 MB 的 Go `.text` 上分块线性解码,
  遇到数据/跳转表就会失步,**后续全部解错** ⇒ 得到「该串无引用」的**假阴性**,
  进而把它写成「字符串没被用」。可靠形态只有一种:**按函数边界(符号表 `st_size` / DWARF subprogram range)解码**。
- **错误串无 RIP 相对引用是正常现象,不是「没找到」**:GoFrame/自研框架常把文案放进**错误码表(数组)**,
  或由共享的 bind/decrypt helper 统一产出 ⇒ 引用链走**数据段的指针表**,你反查不到。
  **止损线:串头与串体都没有直接引用时,停止静态归因**,改用行为差分(第 4 节)。
- **DTO/类字段名 ≠ 线上 wire 字段名**:客户端内部结果类型(如 `XxxEncryptResult`)的字段名
  可能与真正序列化进 JSON 的键不同 —— **wire 名只认序列化调用点那一行**
  (`jSONObject.put("aes_key", …)` / `params.put("data", …)`),不要用 DTO 字段名改请求。
- **全局中间件的应答早于路由匹配**:`401 签名验证失败-N` / `token解析失败-N` 这类由中间件最先产出,
  **与路径是否注册无关**;只有「带合法签名」的请求返 `404` / `ErrCode 65` 才证明路由层在答。
  路由是否存在一律以路由表(元数据/`routes.txt`)为准,**不以中间件响应推论**。
- **反汇编产物一律落盘再 grep**:先 `strings` 落一个独立文件(几十万条),再对文件 grep;
  多行配置在 dump 里会粘成一行,先归一化 `\r\n`/`\r`;判「某值不在这份产物里」必须限域成
  「不在**这份**产物的字符串里」,换产物(APK dex / JS bundle / 另一台二进制 / 配置)重扫。

## 4. 静态走到头之后:行为差分(对照组方法)

拿不到产出者时,用**对照组**把「层」定下来,而不是继续调请求:

- **未知形态被统一拒收时,把同一请求打到「另一方法已证明可用」的兄弟端点**:
  若那边**同码** ⇒ 拒收发生在 handler 之上(体层/边缘层),逐端点调 body/参数名是零信息量动作。
- **每批探测夹一条已知必通对照**(一条你确信会返业务成功的请求);**对照也失败 ⇒ 先修请求器,不要改结论**。
- 判「某面已封」前先按错误码分层:`404`/`65` = 路径或方法错;`已进解密层` 类错 = 载体形态错;
  统一文案(闸门汇总) = 层规则;只有**带合法凭据仍被业务层拒**才算「面封」。

## 5. 收尾要交什么

- 闸门清单:每道闸 = **函数名 + 它读的头/参数 + 它查的表/键 + 未命中时的文案**。
- 契约清单:每个参数族(头名 / 查询串名 / body 键)= **出自哪个函数的哪条指令**,别写「疑似」。
- 归因状态:`已知产出者` / `由错误码表间接产出,静态不可归因(已转行为差分)` —— 后者要显式写出来,别留成悬案。
