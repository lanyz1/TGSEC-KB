## curl 通用探测片段

```python
out = subprocess.check_output(
    'curl -s -k -g -m %d -o /tmp/v.txt -w "%%{http_code} %%{size_download}" %s "%s"' % (m, hdr, url),
    shell=True).decode()
body = open("/tmp/v.txt", encoding="utf-8", errors="replace").read()
```
- **`-g`**:URL 含 `[` `]`(PHP 数组参数如 `filter[]=`)时 curl 当 glob 处理 → 必须 `-g`,否则整批请求报 `ERR:Command ...`
- **`-k`** 证书异常;`-m` 短超时(15–25s)
- **`-o 文件 + -w "状态码 字节数"`**:一次拿「状态码 + 大小 + 裸 body」
- ★ **一发 curl 里同时要 body + 状态码 + 响应头时，全部元数据只用【一对 sentinel】包住、靠 `rfind` 切**:
  `-w "\n@@META@@%{http_code}|%header{set-cookie}@@END@@"` → `k=o.rfind("@@META@@"); net=o.find("@@END@@",k); body=o[:k]`。
  绝不要往同一个 `-w` 里**拼第二段**(`"...@@%{http_code}@@" + "|@@..."`)—— 拼接处极易把引号配对写坏,
  远端报 `SyntaxError: unterminated string literal`,或本机 `JSONDecodeError: Extra data: line N`(元数据被当成 body 尾部),
  而现象看起来像「目标返回了脏 body」。多段元数据一律塞进**同一对** sentinel，用分隔符在 Python 侧拆。
- Host 路由:`-H "Host: <vhost>"`(直连 IP 时)
- **判据式探测先校准真假两档**(不存在的路由 vs 存在的路由),再看响应落在哪档;
  状态码相同就改看**响应体大小/文案**做差分
- **★ 带 `condition` / 过滤参数的批量查询返回"全 0 行"时,先定层再下结论**(0 行有三种成因,顺序排除):
  ① 轨道本身有数据但**参数形状不对/缺必填窗**(实测:带 `condition` 但省略时间窗 ⇒ 0 行);
  ② 参数形状对但**过滤字段在本轨道上恒空**(实测:该轨 `bidder_name` 恒 null ⇒ 按名字 like 查必 0 行);
  ③ 目标确实没有数据。
  定层三件套:**无条件宽窗拉到行**(证轨道活着)→ **拿样本行里真实的 id 重跑同形状过滤查询**(证 condition 形状对)→ 才轮到判目标 0 行。
  缺前三步就把 0 行写成"没有数据",是把**参数错误当业务结论**;结论必须附上"阳性对照命中"的证据,否则只能报"该轨给不出这个维度"。
  ★ **第四种成因:查数的那段代码自己坏了**(调用点与函数定义签名漂移 / 静默 `except`)—— 在观测面上与①②③**完全同形**,都是干净的 0 行。
  判据:独立探针(同接口/同出口/同参数)能拿到满页行,而管线仍报 0 行 ⇒ 直接转 §6。

