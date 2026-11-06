<!-- archived from /root/.hermes/skills/security/go-service-binary-dissection/SKILL.md on 2026-10-21 -->

---
name: go-service-binary-dissection
description: "Use when 从 Go 服务端二进制反推校验逻辑(错误串 xref 归因)。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/go-service-binary-dissection`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/go-service-binary-dissection/…')`，不要相对 `references/legacy/` 解析。

# 未剥离 Go 服务端二进制解剖(错误串 xref → 校验逻辑还原)

适用:拿到**线上服务的未剥离 Go 二进制**(后端 API/钱包/网关),要把黑盒报错与校验行为升到**源码级证据** —— 每句报错由谁发射、先过哪道闸、密钥从哪读。
符号已剥离先走 `go-rust-reverse` 的 pclntab/GoReSym 恢复流程,再回本卡。

## 流程

1. 符号表:**有 Go 工具链时优先 `go tool nm <bin> | grep -i <关键词>` 直接枚举符号族**(中间件/utility/DAO 一次看全;需地址表用 `go tool nm -size -sort address`);无则 `objdump -t <bin> > sym_all.txt`。闸门看 `middleware/`,票工具看 `utility.*JWT*`(keyfunc 常名 `*.func1`),业务看 `logic/`/`dao/` 与 `(*sX).Method` 形态(自带地址+size ⇒ 直接给反汇编范围)。**单函数反汇编 = `go tool objdump -s '<符号>' <bin> > f.asm`**(输出带 `# <addr>` 注释与调用名;逐函数落盘读,比全量 dump 快一个量级;全量只在需全局 xref 时做)。
2. **错误串 xref 归因**(黑盒每句报错 → 发射它的函数):`data.find(b"…")` 得文件偏移,VA=偏移+load delta(Go ELF 常见 0x400000,**先验证再信**) → xref 两条路:① 全量 `objdump -d` 落盘后 `grep '# <VA>'` 一次拿全 lea 引用(注释已解析,最省力;几十 MB 慢但一次复用);② 字节扫全 `.text` 的 RIP 相对 lea(字节形 `48|4c 8d`,modrm&0xC7==0x05,target=指令地址+7+disp32)交叉验证。地址→函数范围映射用 `scripts/find_host_func.py`。③ **两条路都空 = 串被数据段字面量消费**(`[]string` 路由表/白名单):走**数据段指针链** —— string-header `{ptr,len}` 表条目 → 表基址 LE64 指针槽 → slice 描述符 `{ptr,len,cap}`(GNU objdump 对数据地址直出**变量符号名**)→ grep 描述符 VA 拿消费函数;配方见 `references/go-service-error-xref.md` §5,扫描用 `scripts/find_ptr_refs.py`。
3. 反汇编命中函数,解析注释 `# <addr>` 还原 lea 串引用(`fileoff=VA-delta`,NUL 终止 UTF-8 解码);按地址顺序读 = 校验推进顺序;`call` 清单 = 函数故事(见 `gins.Redis`/DAO 调用 = 服务端有状态校验)。
4. 追密钥真源:keyfunc 读的是**编译期全局**(如 `utility.JwtKey`);真源 = **写该全局的 init**(从配置读),不是 read 点 ⇒ 找写入方拿配置键名。
5. **接口调用归因 + 元数据**:`[obj+off]→fun[i]` 间接调用读 `go:itab.<impl>,<iface>` 逐槽解析方法名;**JSON 键名/字段偏移从 `type:<pkg>.<T>` 描述符解码**(size@+0、kind@+23、Fields@+56、StructField 24B)——JWT/JSON claims 键名一次锁死;配方见 `references/go-runtime-metadata-decode.md`。

## 请求契约反查(黑盒报错 → 请求字段名/头名/签名消息)
比「谁报的错」再进一步:**反查请求该带什么**,省掉整轮参数名盲爆。
- **`strings` 先行:框架元数据就内嵌在二进制里,不用先反汇编** —— GoFrame 等框架把路由与契约元数据编译进二进制,`grep -oE 'path:"[^"]{2,60}"[[:space:]]*method:"[a-z]+"'` 一次即出**全量路由表**(实测单服务 281 条,含内部/管理路由);同一 dump 里 `json:"field" v:"required#错误文案"` = 字段名+校验文案,`json:"x" orm:"col"` = 列名,`*pkg.Type` = 请求/响应结构名。**先扫元数据再决定要不要反汇编**:盲爆参数名属于白烧轮次。**元数据路径 ≠ 线上路径**(元数据 `/user/x`,线上 `/v1/user/x`),前缀按已知可用调用定。配方与 sweep 分类见 `references/route-surface-and-contract-extraction.md`。
- **校验标签反查字段名**:GoFrame 风格 tag `Field json:"fieldName" v:"required#错误文案"` —— 黑盒收到「XX不能为空」,`grep 'XX不能为空'` 或 `grep 'json:"'` 即可定位同段落,字段名与文案写在同一 tag 里;全量 `json:"` 拉一遍再按业务关键词过滤最快。
- **ORM 列名**:handler 反汇编里 ORM `Where(...)` 前的 lea 串 = 列名;相邻 lea 分组读 = 一次查询的全部列,配合 Order(`id desc`)/状态值串还原查询语义。
- **请求头名**:`MIMEHeader.Get` 前的 lea 是头名短串;其后 len==0 分支的错误文案 = 该头必填校验(拿到名直接补头重打)。
- **签名中间件消息构造**:抽 `GenerateSignature`/`VerifySignature` 反汇编读 calls —— `mapIter*`+`sort.Strings`(参数按 key 排序取 value)、`fmt.Sprintf` 格式串(如 `%v&` = 拼接模板)、`concatstring2`(逐段拼)、`hmac.New`(算法)、输出编码后段转换调用;按此在外部逐字复刻,别猜格式。**把整个 VerifySignature 读完再定稿**:消息尾巴常再拼 `ts&nonce`,校验侧另带窗口常量(如 ±300s)与 nonce 一次性(Redis 判重)——漏读一段 = 复刻恒失败,别在同一格式上反复试变体。
- 串读法:`objdump -s` 从 lea 注释的 VA 起读;若拿到 16B `{ptr,len}` 对(接口数据/字符串表),按 ptr 二次 dump 才见真字节。

## 坑(铁律)

- load delta 先验证(已知函数首字节比对),别信默认值。
- REX 变体只算 `48/4c`;`49/4d` 是 `[r13+disp]` 寻址,非 RIP 相对。
- 同一句文案可能有**第二份拷贝**(`-1`/`-2` 成对);文件里全部出现位置各查一次。**观测到的变体本身可能 0 字面量**(运行时拼接/格式化,如 `…-2` 搜不到而 `…-1`/`…-0` 在):搜最短唯一前缀枚举全部字面量变体,再用行为差分定它从哪拼出来。
- 独立短文案先按**邻居串判域**再归因:TLS/x509 邻居 = crypto/tls alert 表项,`runtime:` 邻居 = 运行时;都排除后才当业务文案。
- **i18n 文案可能不内嵌**:框架(如 gf)运行时从磁盘 `manifest/i18n` 载入翻译(串 `i18n files loaded in path: %s`),缺翻译常回退返回 key —— 二进制字符串池找不到 ≠ 消息不存在。
- `go tool objdump -s` 单函数 dump 后**先 `wc -l` 验非空**:模式打错会静默产出 0 行文件;拿空文件下过的结论要全部重查。
- 状态码立即数扫描(403=`$0x193` 类)的命中**必须归因到符号**:落在框架内部(如 gf `ghttp.(*Response).WriteStatus` 的 BasicAuth/静态文件分支)= 噪声;业务侧零命中本身是证据(构造在未读代码/内存全局/前沿层),先用活体对照(不存在路由/缺字段/换头)定层再下结论。
- **指针值小端扫描(4/8B)有假阳性**:指令立即数(RIP 位移)会撞上 VA 值;命中后按 `objdump -h` 段表把 FO 归段,**落在 .text 内 = 指令字节,不是数据指针**;数据段命中也要反汇编当地引用点再下结论。
- **xref 归因必须审调用者**:命中串的函数可能不在你这条链上(共用文案/运行时拼接);查它的调用者集合与黑盒放行路径核对——名字会骗人(名为 `SecurityVerify` 的实为资金操作前置验证),存疑先列调用者全集再判。
- **路由拼写/参数名以产物为准,不以英文直觉为准**:真实产品里存在拼写错误的路由(如 `/asstes/getMemberAssetSummary`),按「正确英文」改写后探到的是 404/`ErrCode 65 Not Found` —— 那是**路由不存在**,不是**面被封**;把它记成「已排除」会永久封死一条活路,并污染之后所有轮次。同理参数名与取值格式从 `json:"…"`/`orm:"…"` tag 照抄,别换成自己顺眼的驼峰。
- **宣布某个面「全封」前三条自检**(缺一不可):① 路径逐字来自产物(元数据/bundle/OpenAPI);② 参数名与取值格式逐字来自 tag,且产物里出现的每种形态都试过;③ 该端点要求的**凭据族**自己是否已持有 —— 应用级(appId/appSecret)与用户级(token/secretKey)是两套闸门,注册/登录响应常直接下发 appKey/appSecret,服务端落盘另有 `xxx.appID/appSecret` 一套,两处都要找。之前判死的面要用这三条复核再向用户陈述。
- 别停在「列出符号」:符号表是地图,**错误串 xref + 分支阅读**才是读出逻辑的动作。
- 大文件扫描/解析脚本落盘跑、结果落文件,别 inline 硬猜。
- 接口方法槽位顺序**不可口算**(声明序推理出过错候选)——唯一权威 = itab Fun[] 逐槽符号解析。
- JSON tag/字段偏移别 grep 猜,`type:` 描述符解码是权威(与反汇编 `+0xNN` 互证)。
- symtab 一次 dump 复用;Python 调原生程序用 `D:/…` 路径(MSYS `/d/…` 不认);输出捕获 `python3 x.py > f.txt 2>&1 ; cat f.txt`,stdout 被清时一律落盘+回读。
- 与黑盒互证:中间件含 Redis/DAO 调用 ⇒「真钥=错钥同句」的三发差分结论升级为分支级证据(与 `signed-api-gate-oracle-hunt` 互链)。
- **行为差分先于静态**:同一文案带 `-N` 分级(无 token→`-2`、有 token→`-1` 这类)时,一次只翻一个变量(无/坏/好票、换端点、明文 vs 密文)读后缀梯度——梯度分档 = 闸门判定输入清单,再拿它当静态搜索目标,比盲扫快一个量级。
- **`go tool objdump -s` 前先用 `go tool nm | grep -i <关键词>` 挑符号并看它的类型**:`type:.<pkg>.<T>` / `type:.eq.<pkg>.<T>` 是编译器自动生成的类型比较函数(成百上千行、无业务逻辑),整片 dump 出来读等于白烧轮次(踩过:在一千多行 `type:.eq.*` 里找 handler)。**同名符号有两层:controller 是薄壳,判定与 DB 逻辑在 `logic/` 那个**(`controller/x.(*ControllerV1).M` vs `logic/x.(*sX).M`)—— 要读闸门就 dump `logic/`。
- **头名短串落在远处 VA 时用「长度立即数」定名**:`MIMEHeader.Get` 调用前的 `LEAQ <str>(IP), BX` + `MOVL $0xN, CX`,其中 `$0xN` = 头名长度 —— 配合候选头名(`X-Api-Key` = 9)一步定名,再追该值被送进的 DAO/表名,即得「这个头必须命中哪张表」的闸门语义(实测:`X-Api-Key` → 第三方应用白名单表 → 未命中即 403)。
- **配置键名字符串只是「存在」,不证明该路由启用它**:二进制里出现 `sys_filter_ip` 一类中间件/配置键名(框架自带的整族过滤器常全部编进来)时,**禁止**据此把黑盒 `403` 改写成「IP 白名单」并转去刷 `X-Forwarded-For`/`X-Real-IP`。⇒ 闸门归因一律落到**该路由自己的 handler 分支**(读哪个头 → 查哪张表/哪个全局)+ 多出口同码对照;弱证据(键名字符串)不得推翻已读到的分支级证据,改写只在拿到新的分支级证据时成立。
- **判「密钥不在产物里」必须限域**:单一产物的字符串池零命中只能写「不在*这份*产物里」(换版本 APK / 客户端 so / 配置卷重扫);写成「不在二进制」会被后续轮次当既成事实引用。取串姿势:大二进制先 `strings <bin> > s.txt` 落盘再 grep(单份约 18 万条、可反复复用);grep 多行配置(yml)前先归一化 `\r\n`/`\r`,否则整文件被当一行 ⇒ 字段名/密钥扫描恒空(踩过一整轮)。
- 有状态校验(黑名单/登记簿)读侧与写侧都要读:读侧给判定算子(itab 定 `Exists`/`Del`/`Unlink`),写侧(改密/登出)给键语义与成员 ⇒ 两侧合起来才能反推「键为何存在/何时写入」。

> **中间件语义与请求契约(DWARF 直读闸门/实体/DAO、逐函数反汇编读头名与查询串参数、错误码表类「无 xref」的止损线、静态走不通时的对照组行为差分)见 `references/middleware-and-dwarf-contract-recovery.md`。**
> 完整扫描脚本(可复制)、字符串还原代码、中间件解剖样例、**无代码 xref 的数据段指针链(路由表/白名单→变量名)**、**GoFrame 403/报错判层速查**见 `references/go-service-error-xref.md`;itab/类型描述符/gf 布局与 ABI 读参见 `references/go-runtime-metadata-decode.md`;VA→宿主函数一步定位见 `scripts/find_host_func.py`(配 `go tool nm -size -sort address` 导出的 symtab);**LE64 指针槽扫描见 `scripts/find_ptr_refs.py`**;**路由表/契约元数据的 strings 直取与 sweep 分类、以及「模块/控制器文件全集 + 合并体识别 + 文件模块指纹」见 `references/route-surface-and-contract-extraction.md`**。
