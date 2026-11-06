# 跳板机 runnder 的载荷投递与编码(两个静默杀手)

配合 `references/long-chain-script-engineering.md`(那份讲"怎么写脚本"),这份讲**投递与编码**。
两条都会**静默**毁掉一发:不报错、或报一个与真因无关的错。

## 1. ★runner 只上传「点名的那个脚本」—— 助手模块不会被带过去

`rex2.py` 这类 runner 的形状是「把**指定路径的单个脚本**推到跳板机再执行」。
于是本地这样写必然失败:

```python
# run.py
exec(open("src18h.py", encoding="utf-8").read())   # 本地跑得通
```

跳板机上:

```
FileNotFoundError: [Errno 2] No such file or directory: 'src18h.py'
```

**因为 `src18h.py` 从来没被推过去。** runner 不是 `rsync`、不跟随依赖。

### 正确姿势:合流成单文件再推

```bash
cat helpers.py body.py > run.py      # 单文件 = 助手 + 正文
wc -c run.py                         # ★ 先验字节数,再推
python rex2.py <host> run.py python3 > run_<host>.out 2>&1; echo "RC=$? $(wc -c < run_<host>.out)"
```

- 把**公共探针函数**(连接/请求/报错解析/打印格式)固定放在一个 `*h.py` 里,
  每轮只写"正文"文件,临时 `cat` 合流 —— 既避免重复劳动,又天然满足 runner 的单文件约束。
- `print` 回 `N RC=?` 与输出字节数,**每次都看**;`RC=0` + 字节数明显偏小(如 200~300 B)
  往往就是上面的 FileNotFoundError 被吞进了 `.out`。

## 2. ★base64 进 URL query 必须把 `+` 编码成 `%2B`

`+` 在 query string 里的语义是**空格**。所以把 base64(padding/字符集含 `+`、`/`、`=`)
直接拼进 URL,服务端解出来的密文**已经被改坏**,而且**不报错**,只是校验失败 ——
你会以为是算法/密钥不对,白查半天。

```python
import urllib.parse
q = urllib.parse.quote(token, safe="")     # ★ safe="" ⇒ 连 / 和 = 一起编码
url = "/apidoc/apiData?appKey=admin&apidocToken=" + q
```

- 同理:**能放 body 就别放 query**。POST + JSON body 既免编码、又常常顺手绕掉 WAF 的 URI 规则。
- 判据:同一载荷"手拼 URL"失败、而"放 body"成功 ⇒ 先怀疑 `+`/`%`/`&` 被 URL 语义吃掉。

## 3. 顺带:长脚本的写盘纪律(与上一份交叉)

- 撰写长脚本用 `write_file`(单次 3 KB 级实测可靠),**落盘后必须核字节数**;
  提交式(execute_code)载代码有长度上限,**超限是静默截断**——报
  `SyntaxError: unterminated triple-quoted string literal`,或干脆什么都不打印。
- 见 `references/long-chain-script-engineering.md` §1–§3(症状对照表 + 模块化姿势)。
