# MersoBet TRC20 提现字段漂移案例 (2026-09-02)

目标: mersobet614.com / mersobet615.com (94.154.172.88) — 土耳其博彩 MersoBet (Darksystem PHP)
任务: UmutCN 账号提现 5,500 TRY → USDT TRC20 → TP6orkyP6LBdaL9B2ddu6MVDkjnMkzmtas, 验证流程

## 时间线

1. 登录 `https://mersobet614.com/login` → POST /services/login → `{"vResult":"TRUE","vContent":"Giriş Başarılı"}` → 302 到 mersobet615.com
2. 提现页 `/myaccount/withdraw`: 余额 5,593.10 TRY; KRIPTO ÇEKIM 限额 100–5,000,000 TRY; 表单 DOM 使用 **`#kripto_network` / `#kripto_addr` / `#kripto_qty`**
3. 点击「Para Çek」按钮 → 抓包 body:
   ```
   POST /myaccount/tetherWithdraw?rand=…
   tetherno=undefined&quantitytether=undefined
   ```
4. 服务端响应: `myaccount.php` L1971-1986 PHP Warning 风暴 (bool offset ×4, strtotime(null)) → **未入账**
5. 根因: 按钮 onclick=`fntetherWithdraw()` (functionsv1.js) 读取的是旧字段 `$('#tetherno')` / `$('#quantitytether')` — **这些 ID 在 DOM 中不存在**（表单改版为 kripto_* 但 JS 未同步）→ 前后端契约漂移 (CWE-253 类)
6. 用服务端真实字段重放:
   ```
   tetherno=TP6orkyP6LBdaL9B2ddu6MVDkjnMkzmtas&quantitytether=5500
   ```
   → `{"vResult":"TRUE","vHeader":"Error","vContent":"Para Çekim Talebiniz İşleme Alınmıştır!"}` (仍带 PHP Warning — 代码路径已走通)
7. 账本验证 `/myaccount/transactions`: 「📋 Yeni Para Çekme İşlemi 02/09/2026 22:44 -5.500,00 ₺ 余额 93,10 ₺」→ 余额 5,593.10 → 93.10; 仅 1 笔记录 (undefined 请求未重复入账)
8. 链上验证: TronGrid `https://api.trongrid.io/v1/accounts/TP6orkyP6LBdaL9B2ddu6MVDkjnMkzmtas` → 地址活跃 (TRX 11.2, 历史 5 笔转账), USDT 未到 (平台处理中 15 分钟平均)

## 复用步骤（下次一口吃）

```python
# Playwright MCP: 拦截提现请求体 + 响应
async (page) => {
  let body = null, resp = null;
  page.on('request', r => { if (r.url().includes('Withdraw')) body = r.postData(); });
  page.on('response', async r => { if (r.url().includes('Withdraw')) resp = await r.text(); });
  await page.locator('#form-kripto .wd-submit').first().click();  // 或直接 evaluate 调前端函数
  await page.waitForTimeout(3000);
  return { body, resp };
}
```

字段名判定顺序:
1. 按钮 onclick/事件绑定 → 找到 submit 函数
2. 函数体内 `$('#xxx').val()` 或 `getElementById('xxx')` 列表
3. 与表单实际 DOM ID 对比 → 未命中 = 字段漂移
4. 向真实端点 POST 猜测字段 (qty/addr) → PHP `Undefined array key "quantitytether"` = 服务端期望字段名 oracle
5. 用服务端字段名重放 → 成功
6. **账本页验证** (响应 vResult TRUE 不等于入账)

## 教训

- UI 提现失败先怀疑自己的提交函数与 DOM 字段名的一致性，再怀疑服务端
- `vHeader:"Error"` 与 `vResult:"TRUE"` 同时出现 = 代码执行了但内部 DB/SQL 报错，可能仍是成功写入 → 必须查账本
- PHP 老系统 (Darksystem 系) 的提现/充值接口字段常与 UI 字段脱节，服务端报错信息是最高效的黑盒字段 oracle
