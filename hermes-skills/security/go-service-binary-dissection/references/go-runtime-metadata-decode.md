# Go 运行时元数据解码:itab 定方法 / 类型描述符取字段

配套 SKILL.md。适用:反汇编里遇 `[obj+off]→fun[i]` 间接调用要定「这是哪个接口方法」;或要锁 JSON 键名/结构体字段偏移(如 JWT claims 的 `json:"userId"`)。

## 1. itab:接口调用点 → 真实方法名

- `objdump -t` 全符号里找 `go:itab.<具体类型>,<接口>`(带地址;size=24+8N,N=槽数)。
- Fun[] 从 **itab+0x18** 起,每 8B 一个方法指针 → 在 symtab 里按地址精确命中 = 方法名。
- ★顺序不按源码声明序口算:曾按声明序推出 fun[3]=Unlink,实测逐槽解析 = `Copy,DBSize,Del,Exists` ⇒ **唯一权威 = 逐槽解析**(读出的名字序列可作 sanity check,不作依据)。
- 调用点形态:接口 = {itab,data} 两字(相邻两组接口字段如 [obj+0x18]/[obj+0x28]);`fun[i]` 下标从 0 起。

## 2. 类型描述符:字段名/偏移/JSON tag(权威,替代 grep 猜)

- 符号 `type:<pkg>.<T>` → _type:size@+0、kind@+23(25=struct);StructType:Fields slice @+56 {ptr,len,cap};StructField 24B:{Name ptr@+0、Typ@+8、Offset@+16}。
- Name blob 在 Name 指针处:uvarint(名长)+名字节+uvarint(tag长)+tag 字节。
- 产出 = 字段名+tag+偏移,与反汇编 `+0xNN` 逐一对上;嵌入结构体在此展开为字段(其方法集进 itab,不在这)。
- 样例收获:claims = {UserId int64 `json:"userId"`@+0x00; ApiKey `json:"apiKey"`@+0x08; UserSecret `json:"userSecret"`@+0x18; 内嵌 RegisteredClaims → ExpiresAt@+0x60…} —— JWT 键名由此一次锁死。

## 3. 依赖版本 + 上游源码

- buildinfo 扫 `b"mod\t<模块路径>\t"` 得确切版本;`strings` 里 `(*T).Method` 形态符号作旁证。
- `https://cdn.jsdelivr.net/gh/<org>/<repo>@<ver>/<path>` 拉同版源码读接口方法表/结构布局(jsdelivr 在国内可达,经代理更稳)。
- gf(gogf/gf) v2.x `*gredis.Redis` 布局:config@0x00、adapter@0x08(16B)、8 组接口 @0x18 步进 0x10:Generic,Hash,List,PubSub,Script,Set,SortedSet,String ⇒ 偏移定组 + itab 定方法(如 +0x68/+0x70 = Set 组)。

## 4. 间接调用读参(Go ABI 速记)

- 接口接收者 =(rbx=itab, rcx=data);string=(rdi ptr, rsi len)。
- 变参 []string:newobject 一槽 → 写入 {ptr,len} → `lea rsp,rbx` = slice 头 {ptr,len,cap=1}。
- Sprintf 变参对 = {type,data} 各 16B;整数先 convT64 再填 {type,data}。

## 5. 工作流(防截断/防重复)

- `objdump -t bin > symtab.txt` 只 dump 一次;Python 读文件建 {addr:name} 字典(±0x1000 最近符号兜底);别每轮 subprocess 重跑。
- Python 调原生 objdump.exe 用 `D:/...` 路径(MSYS `/d/...` 不认);捕获 `python3 x.py > f.txt 2>&1 ; cat f.txt`。
- 长脚本分片写、写后验尾;stdout 被环境清除时一律「落盘+回读」。
