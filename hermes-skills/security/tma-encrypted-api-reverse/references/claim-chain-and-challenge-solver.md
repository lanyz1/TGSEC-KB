# 领取链(open → verify-segment×N → claim)与图形挑战自动秒解

适用:红包 / 空投 / 任务奖励类「解锁链接 + 图形验证 + 领取」三段式 TMA(实测站点:`redpack.myqb.io` 系)。

## 1. `open` 的 8 字段契约 —— ★ 唯一致命字段是 `client_ipv4`
前端 bundle 反出的真实 body:
```js
Ur({ token, device_hash, automation_suspected, automation_hits,
     device_profile, tm_version, user_agent, client_ipv4 })
```
| 字段 | 服务端能否独立核验 | 结论 |
|---|---|---|
| **`client_ipv4`** | ✅ 与请求源 IP 对账 | **唯一必填**:缺失 ⇒ `400/40671 解锁链接无效`;补齐 ⇒ **200 `'success'`** |
| `device_hash` / `device_profile` / `tm_version` | ❌ 客户端自证 | 可缺省(前端指纹失败时本就不发) |
| `automation_suspected` / `automation_hits` | ❌ | 无校验(`automation_hits` 必须是 **数组** `[]`,不是 `0`) |
| `user_agent` / `token` | 半 | 必填,内容自由 |

⇒ **铁律:解锁类端点回 `40671`/`40670` 一律先当「我方 body 缺字段」查,不要记成「目标防住」。**
手法:去前端 bundle 的 `post(\`${base}/x\`)` 调用点把**真 body 逐字段抄下来**,再只补「服务端能独立核验的那一个字段」一击命中(实测 9 轮盲试全废,读 bundle 后 1 击成功)。
`open` 返回:`{ session_id, min_interval_ms, challenge:{grid_size,index,total,challenge_id,image_data} }`。

## 2. 会话 TTL 是硬约束 ⇒ 必须「同进程一条命 + 机器秒解」
- ECDH 会话**只在同一进程内存活**;**`open` 后约 60–73s 服务端即判 `400/40705 会话已失效`**。
- ⇒ 「先开好会话 → 人工看图 → 再提交」**架构上必败**(实测人工读图第 2 步就 40705)。
- 正确架构:`setsid nohup python3 run.py > run.log 2>&1 < /dev/null &` 把整条链扔到**远端长驻进程**,
  链内自动解题自动提交,本机只做 `poll`/兜底喂答案(`ans_<i>.txt` 文件通道 + `WAIT_S` 等待窗)。
- 远端长连驱动必须容错:**启动行把 stdout 交给后台会让 paramiko 通道不再收到 EOF ⇒ `recv()` 超时**;
  改为 `recv_ready()` 轮询读缓冲 + 超时(实测这是「假死」的唯一原因)。
- 跳板机依赖先体检:`python3 -c "import PIL,numpy"` 不成则 `pip3 install -q pillow numpy`(否则远端秒解直接 ImportError)。

## 3. 图形挑战(目标图标 vs N×N 网格)求解器三坑
实测语义:图顶 = **目标图标**,下方 `grid_size∈[4,9,16]` 网格,**颜色被随机化 ⇒ 只能按【形状】匹配**;
提交 `{session_id, challenge_id, index, answer=格序号(0 基行优先)}`;`total≤8` 步;每步间隔 `min_interval_ms`(实测 1200)。
纯 PIL+numpy 求解(<1s/图):
1. 行列投影(非背景像素计数)切出目标格与网格;实测 3×3 格边 ~168px、目标格仅 ~72px;
2. 每格取「内容图形」掩码 —— ★ **必须洪水填充掉与格子边界相连的框线,再取最大连通块**;
   ❌ **不可盲目内缩**:首版 `inset=0.16` 把 72px 目标格里**几乎填满**的图标切残 ⇒ 9 格 IoU 全掉到 0.1–0.2、求解器「装死」返回 None;
3. 掩码**保长宽比填充 128×128**(直接 resize 会把长条图标压扁)后两两 IoU,取最大 + 置信门槛。
实测分数:皇冠 **0.945**(与次高差 0.342)/ 礼物 0.867(0.133)/ 小鱼 0.702(0.109)/ 实际判对的 0.671(0.188)。
⇒ ★ **门槛定 `best≥0.62 && margin≥0.15`**;定 0.70 会把 0.671 这种**判对**的答案丢掉(实测因此白烧一个会话,靠人工兜底才过)。

## 4. 证据:只认业务层三条
```
① API 状态机  GET /rp/detail <token> 领前 remaining_amount "1"/status active
              → 领后 remaining_amount "0"/status finished · claims[] 含 {seq,amount,user_id}
② 账单流水    个人中心 > pf_bills → **+1 USDT** · 红包 · <时间>
③ 钱包余额    首页/个人中心 → USDT 1.00 · pf_bal「可用 1 / 冻结 0」
```
三条互不依赖且完全一致 ⇒ 闭环。`claim` 成功响应形如 `{code:0, amount:"1", currency:USDT, message:success}`。

## 5. 配套脚本形态(可直接复用)
- `p1_mint.py` 铸 initData 并**立即存盘**(★ initData 一次性,同份只能握手一次);
- `ipget.sh` 在**跳板机**上取出口 IPv4(四源:api4.ipify.org / ipv4.icanhazip.com / api-ipv4.ip.sb/ip / ipinfo.io/ip),用哪个出口就用哪个填 `client_ipv4`;
- `claim_driver6.py` 本机交互驱动 `start / ans <i> <n> / poll / log`;
- `cb2.py` bot 侧**只读导航器**(支持 `父回调>子回调` 链式;零资金零写入),用于把每一页文本+按钮 dump 成证据。
