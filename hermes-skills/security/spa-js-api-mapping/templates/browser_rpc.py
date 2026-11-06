#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页内 fetch RPC + PoW 自动求解循环模板（由 spa-js-api-mapping 技能提供）

用途：目标站有机器人评分（非浏览器客户端吃假响应）或 X-Verify 式 PoW 挑战时，
用真浏览器上下文发请求，在页面 JS 里自动求解挑战并重放，直到拿到真实业务响应。

适配点（★）：BASE_URL / PATH / METHOD / PAYLOAD / 平台与版本头 / 鉴权头。
依赖：pip install playwright；浏览器可复用 ~/.cache/ms-playwright 缓存（executable_path）。
"""
import json, time, glob, os
from playwright.sync_api import sync_playwright

BASE_URL = "https://TARGET.example"            # ★ 目标站首页（用于就绪 cookie / __ENV）
PATH = "/api/auth/email/register/v2"           # ★ 目标接口路径
METHOD = "POST"                                 # ★
PAYLOAD = {"key": "value"}                      # ★ 请求体；可选字段按真实客户端行为省略，别塞 null/False
AUTH_TOKEN = None                               # ★ 需要鉴权时填 token（放 Auth-Token 头，大小写按 JS 源码）


def find_chrome():
    hits = sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")))
    return hits[-1] if hits else None


JS = r"""
async (args) => {
  const {method, path, payload, token} = args;
  function getCookie(n){const m=document.cookie.match(new RegExp('(^| )'+n+'=([^;]+)'));return m?m[2]:'';}
  async function solveZeros(cnt, b){
    const enc = new TextEncoder(); const buf = enc.encode(b);      // 注意：编码字符串本身，不是 hex 解码
    const data = new Uint8Array(buf.length + 4); data.set(buf);
    const dv = new DataView(data.buffer);
    for (let i = 0; i < (1 << 23); i++) {
      dv.setUint32(buf.length, 2147483648 + i);
      const h = new Uint8Array(await crypto.subtle.digest('SHA-256', data));
      let ok = true;
      for (let n = 0; n < cnt; n++) { const by = h[n>>1]; const nib = (n%2===0)? (by>>4):(by&15); if (nib!==0){ok=false;break;} }
      if (ok) { const ab = new Uint8Array(4); new DataView(ab.buffer).setUint32(0, 2147483648+i);
                return btoa(String.fromCharCode(...ab)); }          // 标准 base64，带填充
    }
    return null;
  }
  async function solveSha256(cnt, b){
    const n = Math.max(1, Math.ceil(cnt));
    const h = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(b.repeat(n))));
    return Array.from(h).map(x => x.toString(16).padStart(2, '0')).join('');
  }
  const hdrs = {'content-type': 'application/json',
                'vnd-bmt-platform': 'browser',                       // ★ 平台头按目标 JS 源码/抓包值
                'vnd-bmt-version': (window.__ENV && window.__ENV.BMT_CODE_VERSION) || 'latest', // ★
                'x-csrftoken': getCookie('csrftoken')};
  if (token) hdrs['Auth-Token'] = token;                            // ★ 头名大小写敏感（按 JS 源码）
  let r = await fetch(path, {method, headers: hdrs, body: JSON.stringify(payload), credentials: 'include'});
  let j = null; try { j = await r.json(); } catch(e) {}
  let cycles = 0;
  while (j && j.func && cycles < 12) {
    let ans = null;
    if (j.func === 'zeros') ans = await solveZeros(j.params.a, j.params.b);
    else if (j.func === 'sha256') ans = await solveSha256(j.params.a, j.params.b);
    if (!ans) break;
    hdrs['x-verify-data'] = r.headers.get('x-verify-data') || '';
    hdrs['x-verify-sign'] = r.headers.get('x-verify-sign') || '';
    hdrs['x-verify-result'] = ans;
    await new Promise(res => setTimeout(res, 1500));
    r = await fetch(path, {method, headers: hdrs, body: JSON.stringify(payload), credentials: 'include'});
    j = null; try { j = await r.json(); } catch(e) {}
    cycles++;
  }
  return {status: r.status, body: j, cycles};
}
"""


def main():
    exe = find_chrome()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe, headless=True,
                                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        ctx = browser.new_context(locale="es-MX", viewport={"width": 1366, "height": 900})
        page = ctx.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=90000)
        time.sleep(8)  # 等 csrftoken / __ENV 就绪
        res = page.evaluate(JS, {"method": METHOD, "path": PATH, "payload": PAYLOAD, "token": AUTH_TOKEN})
        print(json.dumps(res, ensure_ascii=False, indent=1)[:2000])
        browser.close()


if __name__ == "__main__":
    main()
