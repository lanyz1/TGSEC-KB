# 部署残留取证配方:`.git` 取源码 / token 结构与真伪判据

## 1 `.git` 取线上源码(加固 diff 面)
```
GET /.git/config                # remote 指向(private repo)
GET /.git/logs/HEAD             # reflog: clone URL + 每次 pull 的 commit SHA + 分支名
GET /.git/refs/heads/<branch>   # 当前 head SHA
GET /.git/objects/<2>/<38>      # 裸 zlib 流, 需 zlib.decompress 去掉 12 字节头
```
- **顺序**:先 reflog 定身份(clone URL / 分支 / commit 主题),再拿 commit 对象(`objects/<2>/<38>` 解出的 `tree/parent/author/message`)看作者写了什么,最后按 manifest 批量取 blob。
- **loose 命中集 = 工作区被改过的文件**。作者加固时编辑过的文件必然被 `git add` 过,所以那一小撮 loose 对象就是**加固 diff 面**;历史上传过的老文件多在 pack 里(通常 404)。
- manifest 来源二选一:① `/.git/index`(含路径 + blob SHA,最权威);② 已取回的 commit 对象的 tree(递归解 tree 对象,偏慢)。
- **别用 `git-dumper` 一把梭**:它按 pack 索引抓,顺序不对时大批 404 且慢;直取 index→blob 快得多,且命中率更高。
- **命中后必做差分**:取回的 `plugins/<x>/<x>_plugin.php` 与本地同产品**原版** diff,一次读完加固写法(守卫函数/白名单/策略类),比猜快一个量级。

## 2 `authcode` 系(Discuz 血统)载荷结构 —— 解密时最容易踩的坑
```
plaintext = <10 位十进制 pre> + <16 位 md5 校验> + <真载荷>
校验      = substr(md5(<10位pre> + <真载荷> + key_b), 0, 16)
key_a/key_b = md5(key_a)[0:16] 与 key_a 的派生, key = 配置里的 syskey/安全密钥
```
- **解密后必须剥掉前 10 位 + 后随的 16 位校验再切字段**,否则所有字段左移 26 字符,字段长度与含义全判错(会把「真载荷第一个字段」误读成 30 字符的怪值)。
- 载荷常是 `\t` 分隔的三段:`<账号/uid> \t <会话签名> \t <过期 unix 时间戳>`。**先看第 3 段是不是未来时间**判断票是否有效,再看第 2 段长度。
- 会话签名长度是版本指纹:**旧式/自造 = 32hex(md5),加固后的线上 = 64hex(sha256 族)**。

## 3 真票 vs 上一轮自造票
- 判据一(长度/族):真 64hex vs 自造 32hex。
- 判据二(可算出):拿本地脚本重算一遍 —— 若载荷里的签名 == `md5(uid+key+固定常量)` 之类**本仓脚本能算出的值**,那是自造候选,不是目标泄露。
- 判据三(回放):伪造票回放登录页,响应与**无票完全相同**(同长度同文案)⇒ 服务端不认。此时别急着「算法没对」,先怀疑票本身就是自造物。

## 4 会话签名反推的止损线
- 输入要素:uid、账号 key、口令 hash(明文/密文两版)、站点密钥、固定常量、注册时间、group/上级 id。
- 构造空间(一次性跑完):纯哈希串联/带分隔符、HMAC(msg,key) 双向、嵌套(`hash(hash(a)||b)`)、hash-of-旧式 md5、legacy md5 再包一层。`10^5` 量级几十秒可完。
- **0 命中 ⇒ 停**:含义是签名掺了**库里看不到的服务端 pepper** ⇒ 写「无源码不可伪造」,把轮次转去 (a) 明文口令、(b) 遗留安装器/可写面、(c) 同基建独立应用。
- 加固者会写测试(`tests/**` 只回 `PASS:` 断言)明示「改口令/改 key 即使会话失效」——**这是情报不是源码**:它告诉你签名是口令+key 的函数,但拿不到 pepper。

## 5 契约面:未授权方法派发
- 入口形如 `/<module>/?s=<func>/<id>/` 或 `pay/<func>/<trade_no>/` 时,**`<func>` 可控** ⇒ 该插件所有**公开 static 方法**都可点名调用(submit/notify/return/mapi/query…),private 不可。
- 用「点名调用 + 缺字段/类型错」做零写入探测(空参 POST 对注册类端点会真建号)。
- 回调类方法若签名 = `md5(ksort 后 key=val & 连接 + appkey)`,而 appkey 可从配置表读到 ⇒ **签名可自算**,即获得订单级写入原语。这类=资金面,按纪律**只记录不落地**。
