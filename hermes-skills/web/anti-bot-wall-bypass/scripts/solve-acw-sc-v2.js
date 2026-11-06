// Solve an Aliyun WAF "acw_sc__v2" JS challenge and print the cookie to replay.
//
//   node solve-acw-sc-v2.js challenge.html
//   -> COOKIES_JSON:["acw_sc__v2=6ab7e82d686c7084d347c072359012b5060e9af3"]
//
// Run this ON THE HOST/EGRESS you will send the follow-up request from: the cookie
// is bound to the client IP (~1h expiry), so a cookie minted elsewhere is rejected.
// Node 8+ compatible (no String.prototype.matchAll, no optional chaining).
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');

// --- collect inline scripts (regex.exec loop: matchAll needs Node >= 12) ---
const re = /<script[^>]*>([\s\S]*?)<\/script>/g;
const scripts = [];
let m;
while ((m = re.exec(html)) !== null) {
  if (m[1].trim().length > 20) scripts.push(m[1]);
}

// --- minimal DOM the challenge touches ---
const cookies = [];
const doc = {
  createElement: function () {
    return { style: {}, setAttribute: function () {}, appendChild: function () {},
             addEventListener: function () {}, getContext: function () { return null; } };
  },
  getElementsByTagName: function () { return []; },
  querySelector: function () { return null; },
  querySelectorAll: function () { return []; },
  addEventListener: function () {},
  write: function () {},
  body: { appendChild: function () {} },
  head: { appendChild: function () {} }
};
Object.defineProperty(doc, 'cookie', {
  get: function () { return cookies.join('; '); },
  set: function (v) { cookies.push(String(v).split(';')[0]); }
});

const nav = {
  userAgent: process.env.UA ||
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  platform: 'Win32', language: 'zh-CN', languages: ['zh-CN']
};
const loc = { reload: function () {}, href: '', replace: function () {}, assign: function () {} };

const win = {
  document: doc, location: loc, navigator: nav,
  atob: function (s) { return Buffer.from(String(s), 'base64').toString('binary'); },
  btoa: function (s) { return Buffer.from(String(s), 'binary').toString('base64'); },
  setTimeout: function () { return 0; }, setInterval: function () { return 0; },
  clearTimeout: function () {}, clearInterval: function () {},
  console: console, Math: Math, Date: Date, JSON: JSON, String: String, Number: Number,
  Array: Array, Object: Object, RegExp: RegExp, parseInt: parseInt, parseFloat: parseFloat,
  encodeURIComponent: encodeURIComponent, decodeURIComponent: decodeURIComponent
};
win.window = win; win.self = win; win.top = win; win.parent = win; win.globalThis = win;

global.window = win;
global.self = win;
global.document = doc;
global.navigator = nav;
global.location = loc;
global.atob = win.atob;
global.btoa = win.btoa;
global.setTimeout = win.setTimeout;
global.setInterval = win.setInterval;

// --- run their code; a throw after the cookie is set is expected/benign ---
for (let i = 0; i < scripts.length; i++) {
  try {
    new Function('window', 'document', 'navigator', 'location', 'self', 'atob', 'btoa',
                 'setTimeout', 'setInterval', scripts[i])(
      win, doc, nav, loc, win, win.atob, win.btoa, win.setTimeout, win.setInterval);
  } catch (e) {
    // e.g. "Cannot read properties of undefined (reading 'reload')" — the cookie is
    // already captured by then; swallow it so the cookie still gets printed.
  }
}

console.log('COOKIES_JSON:' + JSON.stringify(cookies));
