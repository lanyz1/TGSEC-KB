---
name: api-response-encryption-recovery
description: Use when API responses are base64 ciphertext, not JSON.
---

# API 响应加密还原

## 触发信号
- `Content-Type: application/json` 但 body 是一个**长 base64 串**，里面没有 `{`
- 前端拿到响应先 `JSON.parse(decrypt(res.data))` 才渲染
- 同一接口换 token 后**字节数变化**，说明密文里装的是有结构的数据而不是错误串
- 常见于白标支付 / 博彩 / SaaS 后台：服务端返回「加密体」当卖点，密钥随着前端一起下发

## 核心判断（先记这一条）
**响应加密 != 访问控制。** 密钥如果在前端 bundle 里，加密只是混淆，等价于明文。
交付时写「响应为 AES-128-ECB，密钥硬编码于 `<bundle 路径>` 的 `<常量名>`」，不要写成「数据已加密保护」。

## 步骤

### 1. 原样取 body，别在 shell 里被污染
```bash
curl -sk 'https://T/api/X?id=1' -o /tmp/resp.body -w '%{http_code} %{size_download}\n'
xxd /tmp/resp.body | head -3
```
日志/终端里复制回来的串经常**带引号、换行、转义反斜杠**。这是后面「长度不是 16 的倍数」的 99% 真因。

### 2. 判编码
- `^[A-Za-z0-9+/=\s]+$` → base64
- `^[0-9a-fA-F]+$` 且长度为偶数 → hex
- 先 `re.sub(r'[^A-Za-z0-9+/=]', '', s)` 再 `b64decode(s + '=' * (-len(s) % 4))`

### 3. 从 bundle 里挖密钥
下载前端产物后跑这几条，按命中率排序：
```bash
grep -oE '[A-Za-z_$][A-Za-z0-9_$]{0,3}\s*[=:]\s*"[A-Za-z0-9+/=]{16,32}"' main*.js chun*.js | sort -u
grep -oE '(CryptoJS\.AES|sm4|SM4|encrypt|decrypt|JSEncrypt|subtle\.importKey)' main*.js | sort | uniq -c
grep -oE '(key|iv|secret|salt|pass)[A-Za-z_]*\s*[=:]\s*"[^"]{8,40}"' main*.js | sort -u
```
长度即算法：

| 字面量长度 | 算法 |
|---|---|
| 16 字符 / 16 字节 | AES-128 |
| 24 | 3DES |
| 32 字符 | AES-256 |
| 32 hex 字符 | SM4 |

短变量名（`pe` `iv` `k` `a` `s`）最容易是密钥——别只搜 `key`。

### 4. 模式矩阵暴力，不要靠长度推断模式
**实战坑**：拿到 6,321 字节密文，不是 16 的倍数，直接推断「流模式（CTR/CFB/OFB）」，结果正确答案是 **AES-128-ECB**——那 1 字节差是取串时多带的引号/换行。

正确做法是一次跑满矩阵，用**明文特征评分**选胜者，不用长度推：
```bash
python3 scripts/decrypt_matrix.py /tmp/resp.body "<key1>" "<key2>"
```
评分靠命中 `{"` `"ok"` `"result"` `"message"` `"data"` 这些标记。

### 5. 解填充要宽容
PKCS7 unpad 按 `pt[-1]` 截断，遇到末字节被污染会抛异常。三个候选都试再 JSON.parse：
- `pt[:-pt[-1]]`
- `pt.rstrip(b'\x00')`
- 原样 `pt`
JSON 解析成功即为真。

### 6. 回扫全接口
解通一个不等于解通一批。写一个 `fetch_and_decrypt(url)` 包住整个 action 表重跑，每个 endpoint 落一份 JSON：
```
mr_<Action>_GET.json / mr_<Action>_POST.json
```
这一步才是把「一个洞」变成「一整套数据面」的动作。

## 进阶
- **同一密钥常同时用于请求体**：解通响应后拿同一 KEY 去构造请求，能伪造服务端认为合法的参数（含 tenant/companyId 这类本该由服务端决定的值）
- **加密层不挡方法论**：先解一个无鉴权的 config 接口确认密钥正确，再带着普通用户 token 打同一套——很多系统的 config 接口是 `[AllowAnonymous]`，正好当免费 oracle
- 密钥在多个租户间复用：一份 KEY 往往能解同一运营方全部白标站

## 陷阱
- 把「解不开」当成「加了更强的东西」——大多数情况是取串污染或 IV 猜错，先重取原始 body
- 只试 ECB 一种就放弃，或只试 CBC 一种就放弃；矩阵一次跑完只要几秒
- 解出明文后只看第一屏就下结论：完整字段表里才有 CDN、客服地址、收款地址、`captcha_id` 这些横向资产

## 支持文件
- `scripts/decrypt_matrix.py` — base64/hex × ECB/CBC/CFB/OFB/CTR × 多密钥 × 多 IV 派生，按明文特征打分
