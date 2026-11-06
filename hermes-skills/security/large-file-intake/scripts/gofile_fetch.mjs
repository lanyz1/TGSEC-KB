#!/usr/bin/env node
// gofile 入站取数：guest 票 → 动态签 wt → /contents → 下载
// 用法: node gofile_fetch.mjs <contentId|shareUrl> [outDir]
// 依赖: Node 18+ (global fetch)。首次运行若报 generateWT not exported，
//       先 dump 模块导出键名（Object.keys(ctx)）再改导出取值一行。
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36';
const cid = (process.argv[2] || '').split('/').filter(Boolean).pop();
const outDir = process.argv[3] || '.';
if (!cid) { console.error('usage: node gofile_fetch.mjs <contentId|shareUrl> [outDir]'); process.exit(2); }

async function guestToken() {
  const r = await fetch('https://api.gofile.io/accounts', { method: 'POST', headers: { 'User-Agent': UA } });
  const j = await r.json();
  if (j.status !== 'ok') throw new Error('account: ' + JSON.stringify(j));
  return j.data.token;
}

async function wtModuleSrc() {
  for (const u of ['https://gofile.io/js/wt.obf.js', 'https://gofile.io/dist/js/wt.obf.js']) {
    const r = await fetch(u, { headers: { 'User-Agent': UA } });
    if (!r.ok) continue;
    const t = await r.text();
    if (t.length > 1000) return t;
  }
  throw new Error('wt module not found');
}

async function makeWt(src, token) {
  const sandbox = { navigator: { userAgent: UA, language: 'en-US' }, document: {} };
  sandbox.window = sandbox; sandbox.self = sandbox;
  const ctx = vm.createContext(sandbox);
  vm.runInContext(src, ctx, { timeout: 5000 });
  const fn = ctx.generateWT || (ctx.default && ctx.default.generateWT);
  if (typeof fn !== 'function') {
    throw new Error('generateWT not exported; keys=' + Object.keys(ctx).join(','));
  }
  return await fn(token);
}

async function main() {
  const tok = await guestToken();
  console.log('GUEST ok len=' + tok.length);
  const wt = await makeWt(await wtModuleSrc(), tok);
  console.log('WT ' + String(wt).slice(0, 16) + '...');

  const r = await fetch('https://api.gofile.io/contents/' + cid, {
    headers: { 'User-Agent': UA, Authorization: 'Bearer ' + tok, 'X-Website-Token': wt, 'X-BL': 'en-US' },
  });
  const j = await r.json();
  const d = j.data || {};
  console.log('HTTP', r.status, 'STATUS:', j.status);
  console.log('NAME:', d.name, '| SIZE:', d.size, '| canAccess:', d.canAccess, 'public:', d.public);
  if (!d.link) { console.log('no link; children=', (d.children || []).length); return; }

  fs.mkdirSync(outDir, { recursive: true });
  const out = path.join(outDir, d.name || cid + '.bin');
  const dl = await fetch(d.link, { headers: { 'User-Agent': UA, Authorization: 'Bearer ' + tok } });
  if (!dl.ok) throw new Error('download HTTP ' + dl.status);
  const buf = Buffer.from(await dl.arrayBuffer());
  fs.writeFileSync(out, buf);
  console.log('SAVED', out, buf.length, 'bytes; md5 expected', d.md5);
}

main().catch((e) => { console.error('ERR', e.message); process.exit(1); });
