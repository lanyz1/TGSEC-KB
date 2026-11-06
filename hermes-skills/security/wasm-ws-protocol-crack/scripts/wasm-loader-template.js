// wasm C 库加载模板 (node 环境)
// 用法: 将本文件放到 hxws.js / hxws.wasm 同目录, 修改 wasmUrl 后直接运行
// 提供: Module, client (WebsocketClient 实例), Writer 类, writeData, md5hex
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const RealWS = require('ws');

// ---- 浏览器环境模拟 ----
global.window = global;
global.self = global;
global.document = {
  getElementById: () => null,
  querySelector: () => null,
  createElement: () => ({ style: {}, getContext: () => null }),
  documentElement: { style: {} },
  body: { appendChild: () => {}, style: {} },
  addEventListener: () => {},
  location: { href: 'https://target.com/', hostname: 'target.com', protocol: 'https:' }
};
global.location = global.document.location;
global.navigator = { userAgent: 'Mozilla/5.0', platform: 'Win32', language: 'en' };
global.WebSocket = RealWS;
global.performance = require('perf_hooks').performance;
global.require = require;

// ---- 加载 wasm (注入 wasmBinary 到 glue) ----
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

// ---- 工具 ----
function md5hex(s) { return crypto.createHash('md5').update(s).digest('hex'); }

// ---- Writer 类 (复刻前端 Uc, 与前端 writeData padding 完全一致) ----
class Writer {
  constructor(mcmd, scmd) {
    this.ws = client;
    this.r = this.ws.getSendBufferSize();
    this.s = this.ws.allocSendBuffer(mcmd, scmd, 0);
    if (this.s <= 0) throw new Error('alloc failed s=' + this.s);
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

// ---- writeData (模板驱动) ----
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
      default: throw new Error('unknown type ' + t);
    }
  }
}

// ---- 客户端 (需等待 Module 初始化完成后再调用) ----
setTimeout(() => {
  try {
    client = Module.WebsocketClient.instance();
    console.log('WebsocketClient ready, bufSize=' + client.getSendBufferSize());
    // 启动连接: url, 公网IP, statusCb, msgCb
    // statusCb(status): 3 = SCKSTA_WORK 已连接
    // msgCb(mcmd, scmd, ptr, len, flag): 用 parsePayload 读取数据
  } catch (e) {
    console.error('Client init failed:', e.message);
  }
}, 1500);

// ---- 从 wasm 内存读响应 ----
function parsePayload(ptr, len) {
  const view = new DataView(Module.HEAPU8.buffer);
  const bytes = [];
  for (let i = 0; i < len; i++) bytes.push(view.getUint8(ptr + i));
  return Buffer.from(bytes);
}

module.exports = { Module, Writer, writeData, md5hex, parsePayload };
