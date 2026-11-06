#!/usr/bin/env node
/*
 * 为 obfuscator.io 风格 bundle 的每个 _0x 函数声明注入全局导出桩。
 * 用法: node acorn_inject_exports.js <input.js> [output.js]
 * 前置: npm init -y && npm install acorn --no-audit --no-fund
 *
 * 输出文件用 vm.runInThisContext 执行后, 可从 globalThis.__F2[fnName] 取到函数。
 * 注意: 必须用 acorn 的 node.end —— 不要用平衡大括号(解构默认参数 {k:v=!0x1}={} 会数错)。
 */
const fs = require('fs');
const acorn = require('acorn');

const inFile = process.argv[2];
if (!inFile) { console.error('usage: node acorn_inject_exports.js <input.js> [output.js]'); process.exit(1); }
const outFile = process.argv[3] || inFile.replace(/\.js$/, '') + '.dump.js';

const src = fs.readFileSync(inFile, 'utf8');
const ast = acorn.parse(src, { ecmaVersion: 2022, sourceType: 'module' });

const stubs = [];
(function walk(node) {
  if (!node || typeof node !== 'object') return;
  if (node.type === 'FunctionDeclaration' && node.id && /^(a0_)?_0x[0-9a-f]{6}$/.test(node.id.name)) {
    const n = node.id.name;
    stubs.push([node.end, `;try{globalThis.__F2=globalThis.__F2||{};globalThis.__F2["${n}"]=${n};}catch(__e){}`]);
  }
  for (const key of Object.keys(node)) {
    if (key === 'start' || key === 'end' || key === 'loc' || key === 'range') continue;
    const v = node[key];
    if (Array.isArray(v)) { for (const it of v) walk(it); }
    else if (v && typeof v === 'object') walk(v);
  }
})(ast);

stubs.sort((a, b) => b[0] - a[0]);
let out = src;
for (const [pos, txt] of stubs) out = out.slice(0, pos) + txt + out.slice(pos);
fs.writeFileSync(outFile, out);
console.log(`injected ${stubs.length} export stubs -> ${outFile}`);
