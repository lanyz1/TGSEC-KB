#!/usr/bin/env node
// Drive an obfuscator.io-style challenge script's OWN string decoder instead of
// reimplementing base64 -> decodeURIComponent -> RC4 in another language.
// JS string ops are UTF-16 code units; a latin-1/Python reimplementation
// silently produces mojibake and looks like "encrypted data".
//
// usage: node deobfuscate-obfuscatorio.js challenge.js
//
// Prints (1) every b('0x..','key') call site decoded via the script's own b(),
// (2) any handler the script registered (onload etc.) invoked, and
// (3) recorded DOM side effects (createElement / src / appendChild / value / submit).

const fs = require('fs');
const vm = require('vm');

const file = process.argv[2];
if (!file) { console.error('usage: node deobfuscate-obfuscatorio.js <challenge.js>'); process.exit(1); }
const js = fs.readFileSync(file, 'utf8');

const captured = [];
function mkEl(tag) {
  return {
    tag, _v: undefined, _s: undefined,
    set value(v) { captured.push(['set.value', tag, String(v)]); this._v = v; },
    get value() { return this._v; },
    set src(v) { captured.push(['set.src', tag, String(v)]); this._s = v; },
    get src() { return this._s; },
    set type(v) { captured.push(['set.type', tag, String(v)]); },
    set innerHTML(v) { captured.push(['set.innerHTML', tag, String(v).slice(0, 120)]); },
    submit() { captured.push(['submit', tag]); },
    appendChild(c) { captured.push(['appendChild', tag, (c && (c.src || c.tag || '[el]')) || '[node]']); return c; },
    addEventListener() {},
  };
}

const documentMock = {
  _els: {},
  getElementById(id) { captured.push(['getElementById', id]); return (this._els[id] ||= mkEl(id)); },
  createElement(t) { captured.push(['createElement', t]); return mkEl(t); },
  getElementsByTagName(t) { captured.push(['getElementsByTagName', t]); return [(this._body ||= mkEl('body'))]; },
  querySelector(s) { captured.push(['querySelector', s]); return mkEl('qs'); },
  querySelectorAll: () => [],
  body: mkEl('body'),
  head: mkEl('head'),
  cookie: '',
};

const sandbox = {
  document: documentMock,
  navigator: { userAgent: 'Mozilla/5.0', webdriver: false },
  location: { href: 'https://target/', reload() {}, replace() {}, assign() {} },
  atob: (s) => Buffer.from(String(s), 'base64').toString('binary'),
  btoa: (s) => Buffer.from(String(s), 'binary').toString('base64'),
  decodeURIComponent, encodeURIComponent,
  setTimeout: () => 0, setInterval: () => 0, clearTimeout() {}, clearInterval() {},
  console, Math, Date, JSON, String, Number, Boolean, RegExp, Object, Array, Error, Function, Symbol, Promise,
};
sandbox.self = sandbox;
sandbox.globalThis = sandbox;
sandbox.window = sandbox;

vm.createContext(sandbox);
try {
  vm.runInContext(js, sandbox, { timeout: 8000 });
  console.log('[ok] challenge script executed');
} catch (e) {
  console.log('[exec error]', e.message);
}

// ---- 1. decoded strings, via the script's own decoder -------------------
const sites = [...new Set(
  [...js.matchAll(/\bb\('(0x[0-9a-fA-F]+)','([^']*)'\)/g)].map((m) => m[1] + '|' + m[2]),
)];
console.log(`\n=== decoded strings (${sites.length} call sites) ===`);
for (const s of sites) {
  const [idx, key] = s.split('|');
  try {
    console.log(`  [${idx} '${key}'] ${JSON.stringify(sandbox.b(parseInt(idx, 16), key))}`);
  } catch (e) {
    console.log(`  [${idx} '${key}'] ERR ${e.message}`);
  }
}

// ---- 2. fire registered handlers (onload etc.) --------------------------
const skip = new Set(['atob', 'btoa', 'decodeURIComponent', 'encodeURIComponent',
  'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval', 'Function', 'String',
  'Number', 'Boolean', 'RegExp', 'Object', 'Array', 'Error', 'Math', 'Date', 'JSON',
  'Symbol', 'Promise', 'console']);
console.log('\n=== invoking registered handlers ===');
for (const k of Object.keys(sandbox)) {
  if (typeof sandbox[k] === 'function' && !skip.has(k)) {
    try { sandbox[k](); console.log(`  ${k}() ok`); }
    catch (e) { console.log(`  ${k}() -> ${e.message}`); }
  }
}

// ---- 3. DOM side effects -------------------------------------------------
console.log('\n=== DOM side effects ===');
for (const c of captured) console.log('  ' + c.join(' '));
