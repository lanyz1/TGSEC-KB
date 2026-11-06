#!/usr/bin/env node
/* wasm_bindgen_sign_runner.js — 离线直跑 wasm-bindgen 签名模块（模板，按目标改）
 *
 * 来源: zm1s8x/开云案例（Rust wasm-bindgen, sign(channel, env) → 字符串）。
 *
 * 用法:
 *   node wasm_bindgen_sign_runner.js <wasm> <str1> [str2]    # 一次性
 *   node wasm_bindgen_sign_runner.js <wasm> --loop           # 常驻: stdin "str1 [str2]" 逐行 → stdout 签名
 *   DEBUG=1 node ...                                         # 打印 import 调用序列（诊断 trap）
 *
 * 改造点:
 *   1) 先看长相: node -e "const m=new WebAssembly.Module(require('fs').readFileSync(process.argv[1]));console.log(WebAssembly.Module.imports(m),WebAssembly.Module.exports(m).map(e=>e.name))" <wasm>
 *   2) 导出名默认 sign；参数个数默认 sign(sp,p1,l1,p2,l2)（单字符串模块删掉第二对）
 *   3) malloc/free 参数个数跨版本不同（malloc(len) vs malloc(len,align)）→ 已 try 两版，报错调整
 *   4) import 名按 now/random/floor/throw 模式自动匹配；其余 import 落到兜底 stub（DEBUG 下可见）
 * 诊断: trap(unreachable) 且 DEBUG 下无任何 [stub] 输出 = 输入被输入校验拒绝 → 换精确合法值（别怀疑绑定代码）
 */
const fs = require('fs');

function loadSigner(wasmPath) {
  const mod = new WebAssembly.Module(fs.readFileSync(wasmPath));
  const DEBUG = !!process.env.DEBUG;
  if (DEBUG) console.error('IMPORTS:', JSON.stringify(WebAssembly.Module.imports(mod)));
  const importObj = {};
  for (const imp of WebAssembly.Module.imports(mod)) {
    importObj[imp.module] = importObj[imp.module] || {};
    const n = imp.name;
    if (/throw/.test(n)) importObj[imp.module][n] = () => { throw new Error('wbindgen_throw'); };
    else if (/now/.test(n)) importObj[imp.module][n] = () => { if (DEBUG) console.error('[stub] now'); return Date.now(); };
    else if (/random/.test(n)) importObj[imp.module][n] = () => { if (DEBUG) console.error('[stub] random'); return Math.random(); };
    else if (/floor/.test(n)) importObj[imp.module][n] = (x) => Math.floor(x);
    else importObj[imp.module][n] = () => { if (DEBUG) console.error('[stub] other ' + n); return 0; };
  }
  const inst = new WebAssembly.Instance(mod, importObj);
  const ex = inst.exports;
  const enc = new TextEncoder(), dec = new TextDecoder();
  const u8 = () => new Uint8Array(ex.memory.buffer); // 每次新建：malloc 撑大内存会 detach 旧视图

  function passString(s) {
    const b = enc.encode(s);
    let ptr;
    try { ptr = ex.__wbindgen_malloc(b.length, 1); } catch (e) { ptr = ex.__wbindgen_malloc(b.length); }
    u8().set(b, ptr);
    return [ptr, b.length];
  }

  function sign(...strs) {
    const sp = ex.__wbindgen_add_to_stack_pointer(-16);
    const args = strs.map(passString).flat();
    ex.sign(sp, ...args);
    const v = new Int32Array(ex.memory.buffer);
    const p = v[sp >> 2], l = v[(sp >> 2) + 1];
    const out = dec.decode(u8().subarray(p, p + l));
    try { ex.__wbindgen_free(p, l, 1); } catch (e) { ex.__wbindgen_free(p, l); }
    ex.__wbindgen_add_to_stack_pointer(16);
    return out;
  }
  return { sign };
}

if (require.main === module) {
  const [wasmPath, ...rest] = process.argv.slice(2);
  if (!wasmPath) { console.error('usage: node wasm_bindgen_sign_runner.js <wasm> <str1> [str2] | --loop'); process.exit(1); }
  const { sign } = loadSigner(wasmPath);
  if (rest[0] === '--loop') {
    require('readline').createInterface({ input: process.stdin }).on('line', (line) => {
      const parts = line.trim().split(/\s+/).filter(Boolean);
      if (!parts.length) return;
      try { console.log(sign(...parts)); } catch (e) { console.log('ERR ' + String(e && e.message || e).slice(0, 80)); }
    });
  } else {
    console.log(sign(...rest));
  }
}
module.exports = { loadSigner };
