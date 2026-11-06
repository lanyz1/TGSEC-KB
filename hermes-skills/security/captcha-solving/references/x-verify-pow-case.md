# X-Verify PoW 案例（Torrero/betmaster 白标赌场）

2026-10 实测：betmaster.com.mx 与 betmaster.com（IoM）注册链路 + 业务端点。原始脚本：`/root/engagements/betmaster-mx/`（batch65–71、register_flow.py、/tmp/pow_exact.js）。

## 协议形状
- 带正确边缘头调用敏感端点 → 响应体为挑战：`{"func":"zeros","params":{"a":4,"b":"<64位hex串>"}}`
- 响应头同时给票据：`x-verify-data` / `x-verify-sign`。
- 提交请求加三头：`X-Verify-Data` / `X-Verify-Sign`（照抄响应头原值）+ 答案头（记录用名 `X-Verify-Result`，按现场抓包核对确切拼写）。
- 票据一次消费一次；PoW 过后同会话后续端点不再要。

## zeros 解法（字节级正确版）
```python
import hashlib, base64, struct
def solve_zeros(a, b_str, max_i=1<<24):
    for i in range(max_i):
        n = 2**31 + i
        d = hashlib.sha256(b_str.encode() + struct.pack(">I", n)).hexdigest()
        if d[:a] == "0" * a:
            return base64.b64encode(struct.pack(">I", n)).decode()  # 标准b64，含=
```
- `b_str` = 响应里 b 的**原样字符串**（hex 形态），按 ASCII 编码——JS 端 `TextEncoder.encode(b)` 同理。按 hex 解码再哈希 = 永远解不对（连败根因）。
- a=4 平均 ~2.4 万次迭代（毫秒-百毫秒）；a=5 约 4 倍。

## 对标自检流程（防实现漂移）
1. 从站点 bundle 抽原版求解函数拼成 node 脚本（如 /tmp/pow_exact.js），跑同输入。
2. Python 与 node 输出必须**逐字节一致**（含 b64 填充）再上靶场。
3. 端到端验证：解完打 feed 类端点，回业务参数错误（「缺参数」）即全过。

## 常见坑
- base64 用标准 btoa 语义（`+` `/` `=`），不要 url-safe/base64url。
- nonce 是 4 字节**大端** uint32；别写小端。
- 429 = 限速；退避/换出口后挑战会重新发（重新解）。
- 该平台 PoW 与「机器人评分」两层叠着：脚本 TLS 会被喂假业务错误（见 SKILL.md §8），PoW 对了也可能先被假错误误导。
