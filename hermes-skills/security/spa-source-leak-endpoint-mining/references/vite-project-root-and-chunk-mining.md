# Vite 工程根 → chunk 图 → 后端端点

完整命令与案例证据。适用于 Vite/Vue3 SPA，后端是扁平 PHP 或 REST API；目录爆破全 404，但前端能跑。

## 0. 先定协议、再定出口

```bash
curl -k -sS -m 8 -o /tmp/h -w 'https %{http_code} %{size_download}\n' "https://HOST:PORT/"
curl    -sS -m 8 -o /tmp/h -w 'http  %{http_code} %{size_download}\n' "http://HOST:PORT/"
```

- HTTP 回 `400`/`000`、HTTPS 回 `200` → HTTPS-only，不要写“端口死”。
- 同一主机的 `:80` 若 301 到 `https://HOST:4455/`，`Location` 直接给出真实 scheme + port。
- 目标有 IP 白名单时走 `curl -k --socks5-hostname 127.0.0.1:1080`；直连 403 不代表端点在应用层不存在。

## 1. 工程根裸奔

```bash
BASE="https://HOST:PORT"
for f in package.json vite.config.js vite.config.ts package-lock.json; do
  echo "=== $f"
  curl -k -sS -m 10 -D /tmp/h "$BASE/$f" -o "/tmp/$f"
  head -3 /tmp/h
  wc -c "/tmp/$f"
  head -c 400 "/tmp/$f"; echo
done
```

判定：

- `package.json` 能 `json.loads`，且含 `"name"`/`"dependencies"` → 真工程根泄露。
- `vite.config.js` 含 `defineConfig`、`server.proxy`、`target` → 真配置泄露；proxy target 只是线索，可能 DNS 已撤。
- `Content-Type: text/html` / 解析失败 → SPA fallback，不是泄露。
- `/src/*` 全 404 不影响工程根文件 200；两件事分开判。

## 2. 抽 chunk 图

主入口通常是 `/assets/index-*.js`。Vite 6 的 minified 形态：

```js
const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/A-abc.js","assets/B-def.js"])))=>i.map(i=>d[i]);
```

脚本（主入口找不到 `__vite__mapDeps` 就遍历所有已下载 JS）：

```python
import re, json, pathlib

def extract(path):
    s = pathlib.Path(path).read_text(errors='ignore')
    names = []
    m = re.search(r'__vite__mapDeps=\(i,m=__vite__mapDeps,d=\(m\.f\|\|\(m\.f=(\[[^\]]*\])\)\)\)', s)
    if m:
        try:
            names += json.loads(m.group(1))
        except Exception:
            pass
    names += re.findall(r'["\']((?:assets|js|\.)/?[A-Za-z0-9_.\-/]+\.js)["\']', s)
    return names

names = []
for p in pathlib.Path('.').rglob('*.js'):
    names += extract(p)
seen = []
for n in names:
    n = n[2:] if n.startswith('./') else n.lstrip('/')
    if n not in seen:
        seen.append(n)
pathlib.Path('chunks.txt').write_text('\n'.join(seen))
print(len(seen))
```

若只看到 `__vite__mapDeps([0,1,2])` 的索引数组，先找到同一文件里的 `m.f=[...]` 文件列表，再按索引映射。

## 3. 串行下载

```bash
BASE="https://HOST:PORT"
mkdir -p assets
while read -r n; do
  out="assets/$(basename "$n")"
  [ -s "$out" ] && continue
  curl -k -sS -m 20 --socks5-hostname 127.0.0.1:1080 "$BASE/$n" -o "$out"
done < chunks.txt
```

不要 `xargs -P8`：弱站/代理下常见 `exit -1`、空文件、半包。串行 + `[ -s ] && continue` 断点续传最稳。

## 4. 端点提取与验证

```python
import re, pathlib
pat = re.compile(r'["\'`](/?[A-Za-z0-9_./-]+\.php(?:\?[^"\'`]*)?)["\'`]')
hits = set()
for p in pathlib.Path('assets').rglob('*.js'):
    hits.update(pat.findall(p.read_text(errors='ignore')))
print('\n'.join(sorted(hits)))
```

再加 `/api/...`、`/v1/...` 等 REST 路径；按前缀分组，先看 `php_api/`、`admin/`、`user/`、`pay/`、`withdraw/`。

验证顺序（只读）：

1. 无 token GET → 记录状态/长度/CT。
2. 有 token GET → 同上；`200 + 业务 JSON` 才是面。
3. 新端点先回对应 route chunk 读字段名，再考虑 POST；`old_pwd/new_pwd/confirm_pwd` = 自助改密，不是 IDOR。

## 5. 案例证据（2026-10）

- Vite SPA 工程根 `package.json`/`vite.config.js` 均 200；`/src/*` 全 404。
- 主入口 `__vite__mapDeps` 解出 **82 个 chunk**，串行全量落地。
- 从 chunk 正则掏出 **9 个此前目录爆破没发现的 PHP 端点**（`change_pwd.php`、`get_answer.php`、`user_recharge.php`、`user_bank_card.php`、`roulettedraw.php` 等）。
- 验证结果：`change_pwd` 是 `old_pwd/new_pwd/confirm_pwd` 自助改密；其余多为 `401`/参数错误；时间盲注重测回落基线，不是 SQLi。
- 另一个 IP 的同一套 `/php_api`：同 token 回同一业务对象、同一 fatal 错误路径 → 同库镜像，不是新数据面。

## 6. 收线条件

- 工程根文件是 HTML fallback → 不是泄露，停止。
- chunk 图拿完、端点全 401 且无参数契约 → 记录为负，转下一个面。
- 新 IP 同 token 同数据同错误路径 → 标“镜像”，不再重复拖库。
