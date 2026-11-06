#!/usr/bin/env node
/* Dump strings from a javascript-obfuscator bundle (string-array + RC4).
 *
 * Usage:  node deob_js_strings.js <bundle.js> [outdir]
 *
 * How it works: obfuscated bundles declare top-level `function l()` (returns the
 * encoded string array) and `function u(index, key)` / `function V(index, key)`
 * (RC4 decoder, internally `index = index - <offset>`, cached by index+key).
 * We run the file in a vm sandbox with a fake window/document so the trailing
 * IIFE can blow up harmlessly, then call l()/u() ourselves.
 *
 * Keys: the RC4 key is passed at every call site as a string literal 2nd arg
 * (e.g. `(0x230,'tk4r')`). We harvest candidates from the source text.
 *
 * Note: `npx webcrack <f> -o deob` sometimes produces nothing at all; this
 * harness is the fallback that actually works.
 */
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const SRC_PATH = process.argv[2];
if (!SRC_PATH) { console.error('usage: node deob_js_strings.js <bundle.js> [outdir]'); process.exit(2); }
const OUTDIR = process.argv[3] || path.dirname(SRC_PATH);
const SRC = fs.readFileSync(SRC_PATH, 'utf8');

// ---- harvest RC4 key candidates from call sites ----
const keys = new Set();
for (const m of SRC.matchAll(/,\s*'((?:[^'\\]|\\.)*)'\s*\)/g)) keys.add(m[1]);
for (const m of SRC.matchAll(/\(\s*0x[0-9a-fA-F]+\s*,\s*'((?:[^'\\]|\\.)*)'\s*\)/g)) keys.add(m[1]);
console.error(`[i] key candidates: ${keys.size}`);

// ---- sandbox (fake DOM so the loader IIFE dies quietly) ----
const el = () => ({ style: {}, dataset: {}, setAttribute() {}, appendChild() {}, addEventListener() {} });
const sandbox = {
  window: { sessionStorage: { getItem: () => null, setItem() {} }, location: { href: 'https://x/', replace() {} } },
  document: Object.assign(el(), { documentElement: el(), head: el(), body: el(),
    createElement: el, getElementsByTagName: () => [], querySelector: () => null,
    addEventListener() {}, cookie: '' }),
  navigator: { userAgent: 'Mozilla/5.0' }, location: { href: 'https://x/' },
  console, Math, Date, JSON, setTimeout, setInterval, clearTimeout, clearInterval,
};
sandbox.globalThis = sandbox;
const ctx = vm.createContext(sandbox);
try { vm.runInContext(SRC, ctx, { timeout: 20000 }); }
catch (e) { console.error('[i] run error (ignored): ' + String(e).slice(0, 160)); }

// ---- dump ----
const arr = typeof sandbox.l === 'function' ? sandbox.l() : null;
console.error(`[i] array len: ${arr ? arr.length : 0}; decoders: u=${typeof sandbox.u} V=${typeof sandbox.V}`);
const decoders = [sandbox.u, sandbox.V].filter(f => typeof f === 'function');
const out = new Set();
for (const dec of decoders) {
  for (const k of keys) {
    for (let i = 0; i < (arr ? arr.length + 1000 : 1200); i++) {
      try {
        const v = dec(i, k);
        if (typeof v === 'string' && v.length > 2 && /^[\x20-\x7e\u4e00-\u9fff]+$/.test(v)) out.add(v);
      } catch (e) { /* index/salt miss */ }
    }
  }
}
const list = [...out].sort();
const dst = path.join(OUTDIR, path.basename(SRC_PATH) + '.strings.txt');
fs.writeFileSync(dst, list.join('\n'));
console.error(`[+] ${list.length} strings -> ${dst}`);

// highlight the stuff that usually matters
for (const ln of list) {
  if (/\/static\/js\//.test(ln) || /CONFIG|cdn|api|token|key/i.test(ln)) console.log(ln);
}
