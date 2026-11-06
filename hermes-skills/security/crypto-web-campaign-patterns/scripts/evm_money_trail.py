#!/usr/bin/env python3
"""链上定性探针：判断一个质押/理财盘是『授权盗U』还是『存款即变现庞氏』。

用法:
    python3 evm_money_trail.py --staking 0xSTAKING --vvv 0xTOKEN \\
        [--rpc https://base-mainnet.g.alchemy.com/v2/KEY] [--chain base] \\
        [--vdec 18] [--weth 0xWETH]

产出（全部只读，无任何写链操作）:
  1. 合约互联: staking.owner / vvvToken / treasury / payout / rootReferrer
               treasury.router / projectWallet；payout.feeWallet
  2. 托管检查: staking / treasury / payout / projectWallet 的 native + token 余额
     → staking 的 token 余额 ≈ 0 ⇒ 本金不留合约（『存款即变现』信号）
  3. 变现流水: Treasury 累计卖出的 TOKEN 数量；projectWallet 收到的 native 及来自谁
               payout 收到的 native 及资金来源（谁在回填）
  4. 兑付存续: PrincipalWithdrawn / RewardClaimed / PrincipalPaid / RewardPaid 事件计数
     （Alchemy 全量 eth_getLogs 常被拒 → 走 Blockscout v1 getLogs）
  5. 价格口径: 合约 getLatestPrice() vs 路由 getAmountsOut 反推市场价

依赖: pycryptodome (Crypto.Hash.keccak) — 用于算 selector / topic0。
      uv pip install pycryptodome --system
注意: 需要 Alchemy RPC 才能跑第 3 节（alchemy_getAssetTransfers 为 Alchemy 专有）。
"""
import argparse, json, ssl, urllib.request

CTX = ssl.create_default_context()

BLOCKSCOUT = {
    'base': 'https://base.blockscout.com',
    'eth': 'https://eth.blockscout.com',
    'bsc': 'https://bsc.blockscout.com',
}

DEFAULT_WETH = {
    'base': '0x4200000000000000000000000000000000000006',
    'eth': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
}


def keccak_hex(data: str) -> str:
    from Crypto.Hash import keccak
    k = keccak.new(digest_bits=256)
    k.update(data.encode())
    return k.hexdigest()


def topic0(sig: str) -> str:
    return '0x' + keccak_hex(sig)


def sel(sig: str) -> str:
    return '0x' + keccak_hex(sig)[:8]


def pad32(hexstr: str) -> str:
    return hexstr[2:].lower().rjust(64, '0')


class Rpc:
    def __init__(self, url):
        self.url = url

    def __call__(self, method, params, timeout=30):
        req = urllib.request.Request(
            self.url,
            data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode(),
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return json.loads(r.read())
        except Exception as e:
            return {'error': str(e)}


def http_json(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'error': str(e)}


def is_addr(x):
    return isinstance(x, str) and x.startswith('0x') and len(x) == 42


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--staking', required=True)
    ap.add_argument('--vvv', required=True, help='质押代币地址')
    ap.add_argument('--rpc', default=None, help='Alchemy RPC（第3节必需）')
    ap.add_argument('--chain', default='base', choices=list(BLOCKSCOUT))
    ap.add_argument('--weth', default=None)
    ap.add_argument('--vdec', type=int, default=18, help='质押代币小数位')
    a = ap.parse_args()

    rpc = Rpc(a.rpc or 'https://mainnet.base.org')
    WETH = a.weth or DEFAULT_WETH[a.chain]
    ST = a.staking

    def call(to, signature):
        j = rpc('eth_call', [{'to': to, 'data': sel(signature)}, 'latest'])
        return j.get('result')

    def as_addr(r):
        return ('0x' + r[-40:]) if isinstance(r, str) and len(r) == 66 else r

    def native(addr):
        r = rpc('eth_getBalance', [addr, 'latest']).get('result')
        return int(r, 16) / 1e18 if isinstance(r, str) and r.startswith('0x') else None

    def token_bal(token, holder):
        data = '0x70a08231' + pad32(holder)
        r = rpc('eth_call', [{'to': token, 'data': data}, 'latest']).get('result')
        if isinstance(r, str) and r.startswith('0x'):
            return int(r, 16) / (10 ** a.vdec)
        return None

    def code_len(addr):
        r = rpc('eth_getCode', [addr, 'latest']).get('result', '')
        return (len(r) - 2) // 2 if isinstance(r, str) and r.startswith('0x') else None

    print('=' * 68)
    print('1) 合约互联')
    links = {}
    for sig in ['owner()', 'vvvToken()', 'treasury()', 'payout()', 'projectWallet()', 'rootReferrer()']:
        v = as_addr(call(ST, sig))
        links[sig] = v
        print(f'   staking.{sig:18s} {v}')

    treasury = links.get('treasury()')
    payout = links.get('payout()')
    prj = links.get('projectWallet()')
    router = None
    if is_addr(treasury):
        router = as_addr(call(treasury, 'router()'))
        p2 = as_addr(call(treasury, 'projectWallet()'))
        prj = p2 if is_addr(p2) else prj
        print(f'   treasury.router()          {router}')
        print(f'   treasury.projectWallet()   {prj}')
    if is_addr(payout):
        print(f'   payout.feeWallet()         {as_addr(call(payout, "feeWallet()"))}')

    print()
    print('=' * 68)
    print('2) 托管检查（staking 的 token 余额 ≈ 0 ⇒ 本金不留合约）')
    for name, addr in [('staking', ST), ('treasury', treasury), ('payout', payout), ('projectWallet', prj)]:
        if not is_addr(addr):
            continue
        print(f'   {name:14s} {addr}  code={code_len(addr)}  '
              f'native={native(addr)}  token=<REDACTED>, addr)}')

    print()
    print('=' * 68)
    print('3) 变现流水 (alchemy_getAssetTransfers)')
    if not (a.rpc and 'alchemy' in a.rpc):
        print('   ! 需要 --rpc 指向 Alchemy，跳过（该 API 专有）')
    else:
        def transfers(**kw):
            out, page = [], None
            for _ in range(20):
                p = {'fromBlock': '0x0', 'toBlock': 'latest', 'maxCount': '0x3e8',
                     'order': 'desc', 'excludeZeroValue': True, **kw}
                if page:
                    p.update(page)
                j = rpc('alchemy_getAssetTransfers', [p]).get('result') or {}
                ts = j.get('transfers') or []
                out += ts
                page = j.get('pageKey')
                if not page or not ts:
                    break
                page = {'pageKey': page}
            return out

        def summarize(ts, label):
            tot = sum(float(t.get('value') or 0) for t in ts)
            print(f'   {label}: {len(ts)} 笔, 累计 {tot:,.6f}')
            src = {}
            for t in ts:
                addr = (t.get('from') if 'from' in label.lower() else t.get('to')) or ''
                src[addr] = src.get(addr, 0) + float(t.get('value') or 0)
            for k, v in sorted(src.items(), key=lambda x: -x[1])[:5]:
                if k:
                    print(f'      {k}  {v:,.6f}  code={code_len(k)}')
            return tot

        if is_addr(treasury):
            ts = transfers(fromAddress=treasury, category=['erc20'], contractAddresses=[a.vvv])
            print(f'   Treasury 卖出 TOKEN: {len(ts)} 笔, 累计 '
                  f'{sum(float(t.get("value") or 0) for t in ts):,.4f}')
        if is_addr(prj):
            summarize(transfers(toAddress=prj, category=['internal']),
                      'projectWallet 收到 native（来源）')
        if is_addr(payout):
            summarize(transfers(toAddress=payout, category=['external', 'internal']),
                      'payout 收到 native（谁在回填）')

    print()
    print('=' * 68)
    print('4) 兑付存续（Blockscout v1 logs；Alchemy 全量 getLogs 常被拒）')
    bs = BLOCKSCOUT[a.chain]
    for label, addr, sig in [
        ('PrincipalWithdrawn', ST, 'PrincipalWithdrawn(address,uint256,uint256)'),
        ('RewardClaimed', ST, 'RewardClaimed(address,uint256)'),
        ('PrincipalPaid', payout, 'PrincipalPaid(address,uint256,uint256)'),
        ('RewardPaid', payout, 'RewardPaid(address,uint256,uint256,uint256)'),
    ]:
        if not is_addr(addr):
            continue
        url = (f'{bs}/api?module=logs&action=getLogs&address={addr}'
               f'&topic0={topic0(sig)}&fromBlock=0&toBlock=latest')
        d = http_json(url)
        res = d.get('result')
        if res is None:
            print(f'   {label}: ERR {str(d)[:110]}')
        else:
            print(f'   {label}: {len(res)} events')
    print('   注: 计数为 0 不一定是『没人用』—— 事件签名猜错也会得 0，先核 ABI。')

    print()
    print('=' * 68)
    print('5) 价格口径')
    r = call(ST, 'getLatestPrice()')
    if isinstance(r, str) and len(r) == 66:
        print(f'   合约 getLatestPrice() = {int(r, 16) / 1e18:,.6f}  ← 自有预言机，常虚高')
    if is_addr(router):
        data = (sel('getAmountsOut(uint256,address[])')
                + format(10 ** 18, '064x')          # amountIn = 1 TOKEN
                + format(0x40, '064x')              # offset to address[]
                + format(2, '064x')                 # array length
                + pad32(a.vvv)
                + pad32(WETH))
        rr = rpc('eth_call', [{'to': router, 'data': data}, 'latest']).get('result')
        if isinstance(rr, str) and rr.startswith('0x'):
            body = rr[2:]
            words = [body[i * 64:(i + 1) * 64] for i in range(len(body) // 64)]
            try:
                out = int(words[-1], 16) / 1e18
                print(f'   路由 getAmountsOut(1 TOKEN) = {out:.18f} native')
                print(f'   → 别用平台自报价；与 CoinGecko/交易所真实价对比，差价即账面虚高倍数')
            except Exception:
                print('   路由 getAmountsOut 解析失败:', rr[:90])

    print()
    print('判读:')
    print('  staking token 余额 ≈ 0 且 treasury 只当中转          → 存款即变现（庞氏档）')
    print('  全合约仅 stake() 一处 transferFrom                   → 不是 approve-drainer')
    print('  PrincipalWithdrawn > 0                               → 仍在兑付，非已跑路')
    print('  合约价 vs 路由/市价差 2x                               → 账面金额虚高，汇报要两栏')
    print('  payout 资金来自运营方 EOA 而非营收                    → 靠回填撑着的盘')


if __name__ == '__main__':
    main()
