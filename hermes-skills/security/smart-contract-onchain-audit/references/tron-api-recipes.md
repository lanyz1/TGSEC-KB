# TRON 链上审计端点实测清单

全部请求：先 `unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy`，
再加 `curl -s --noproxy '*'`。否则会被本机常驻代理污染或超时。

## 一、TronGrid（稳，首选）

### 取 ABI + 字节码
```
POST https://api.trongrid.io/wallet/getcontract
body: {"value":"<T地址base58>", "visible": true}
→ { bytecode, name, abi:{entrys:[...]} }
```
- `abi.entrys[].type` ∈ `Function` / `Event` / `Error` / `Constructor`
- **Error 条目要单独抽出来算 selector**，它们是判权限的最强信号
- ⚠️ ABI 常不完整 ⇒ 用 `scripts/dispatcher_extract.py` 从字节码补齐

### 只读调用 / 权限仿真（同一个端点）
```
POST https://api.trongrid.io/wallet/triggerconstantcontract
body: { owner_address: "<模拟调用者base58>", contract_address: "<T地址>",
        function_selector: "transferAsset(address,address,uint256)",
        parameter: "<ABI编码的hex，不要0x>", visible: true, call_value: 0 }
→ { constant_result:["<hex结果>"], result:{ result:true, message:"REVERT opcode executed" } }
```
- **不广播、不改状态** —— 做权限矩阵仿真的关键
- 也可以绕开 `function_selector` 解析：直接给 `data` 字段发原始 calldata
  （测 **ABI 里没有的隐藏 selector** 时必须这样）
- ABI 编码速查：地址 = `%024x` + 后 40 位 hex；uint = `%064x`；
  多参数直接拼接（每个 64 hex 一段）

### 账户
```
GET https://api.trongrid.io/v1/accounts/<T地址>
GET https://api.trongrid.io/v1/accounts/<T地址>/transactions?only_confirmed=true&limit=50
→ data[0].{ type, balance, trc20, create_time, account_name, owner_permission, active_permission }
```
- `type` = `Contract` ⇒ 是合约；缺失/None ⇒ 普通 EOA
- `account_name` 是 **hex 编码的 ASCII**，解出来常有信息
  （实测解出 `CreatedByContract`，直接证伪了「代理」判断）
- `trc20` 是索引、可能滞后 ⇒ 余额以 `balanceOf` 合约调用为准

## 二、TronScan API（补充）

```
GET https://apilist.tronscanapi.com/api/contract?contract=<T地址>
→ name / verify_status / is_proxy / proxy_implementation / creator / date_created / balance
   ⚠️ is_proxy 与 proxy_implementation 会误报（可指向无字节码的占位地址）
   ⇒ 必须用字节码自查 delegatecall，别信这个字段

GET https://apilist.tronscanapi.com/api/filter/trc20/transfers
    ?limit=50&start=0&sort=-timestamp&address=<T地址>          # 双向（覆盖不全）
    ?limit=50&start=0&sort=-timestamp&fromAddress=<T地址>      # ★ 出金专用
    ?limit=50&start=0&sort=-timestamp&relatedAddress=<T地址>   # 以转入为主，会漏出金
→ token_transfers[] 或 data[]  { block_ts, from_address, to_address, quant, tokenInfo }
```
- **追出金一定要单独用 `fromAddress`**，否则会得出「钱还在」的错误结论

### 实测不好用的（别浪费时间）
- `api/contract/source-code`、`api/contract/verify/source/code`、`api/contract/solidity`、
  `api/contract/detail`、`api/solidity/contract` —— 未开源时多为空响应
  ⇒ 试 1~2 个即转字节码路线
- `api/contracts?...&creator=<地址>` 与 `&q=<名字>` —— 未按预期过滤（返回全局列表）
  ⇒ 部署者历史改用「查部署者的交易 + 逐个 getcontract」自己串
- `api/accountv2` —— 返回非 JSON；改用 TronGrid `/v1/accounts/<addr>`

## 三、常用 selector 速查（keccak256 前 4 字节）

权限/错误类：
```
82b42900  Unauthorized()
9e87fac8  Paused()
3ee5aeb5  ReentrancyGuardReentrantCall()
5274afe7  SafeERC20FailedOperation(address)
f1d80ab1  EscrowNotFound()
cf479181  InsufficientBalance(uint256,uint256)
9c8d2cd2  InvalidRecipient()
929ce051  InvalidParticipants()
ed28d089  DepositBelowMinimum(uint256,uint256)
9996b315  AddressEmptyCode(address)
b06ebf3d  FailedDeployment()
2c5211c6  InvalidAmount()
f9984565  UnexpectedTokenAmount()
```
可升级函数（**用来证伪「可升级」**）：
```
3659cfe6  upgradeTo(address)
0900f010  upgrade(address)
d784d426  setImplementation(address)
691bd2ae  setImpl(address)
c4d66de8  initialize(address)
19ab453c  init(address)
bf8bdac1  setService(address)
5bb47808  setFactory(address)
```

## 四、地址工具（纯 stdlib，无需 web3）

base58check = 版本字节 + 20 字节 + SHA256d 前 4 字节：
```python
from Crypto.Hash import SHA256
ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58(b):
    n = int.from_bytes(b, "big"); s = ""
    while n > 0:
        n, r = divmod(n, 58); s = ALPH[r] + s
    for by in b:
        if by == 0: s = "1" + s
        else: break
    return s
def hex41_to_t(h):          # '41' + 20字节hex → 'T...'
    raw = bytes.fromhex(h[:42] if h.startswith("41") else "41" + h[-40:])
    return b58(raw + SHA256.new(SHA256.new(raw).digest()).digest()[:4])
def t_to_hex(a):            # 'T...' → '41' + 20字节hex
    n = 0
    for ch in a: n = n * 58 + ALPH.index(ch)
    return n.to_bytes(25, "big").hex()
```
ABI 参数里的地址是 **20 字节无前缀**，转 base58 要自己补 `41`。
