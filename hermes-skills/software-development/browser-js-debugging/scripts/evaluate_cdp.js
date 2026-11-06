// evaluate_cdp.js —— 带超时的页面取值探针（主线程若被占住会返回 timeout 而不是挂住）
//
// 为什么需要它：页面主线程被同步阻塞（原生对话框 / 同步 IO）或饥饿时，
//   裸的 Runtime.evaluate 会把连接**挂着不报错**，调用脚本静默卡死。
//   本脚本给 evaluate 带 CDP 自身 timeout + Promise.race 自救，永不静默卡住。
//
// 依赖：ws（装到独立 scratch 工程，用 WS_PATH 指过去，别污染被测工程）
//   mkdir -p <scratch> && cd <scratch> && npm init -y && npm i ws
// 用法：WS_PATH=<scratch>/node_modules/ws node evaluate_cdp.js "<表达式>" [--port 9222] [--ms 4000]
//   --port  CDP 远程调试端口（Chrome --remote-debugging-port=<port>）
//   --ms    evaluate 超时毫秒（默认 4000）
const http = require('http')
const WS = require(process.env.WS_PATH || 'ws')
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d }
const EXPR = process.argv[2] || 'document.title'
const PORT = Number(arg('port', 9222))
const MS = Number(arg('ms', 4000))

const getJSON = (p) => new Promise((res, rej) => {
  http.get({ host: '127.0.0.1', port: PORT, path: p }, (r) => {
    let s = ''
    r.on('data', (c) => (s += c))
    r.on('end', () => { try { res(JSON.parse(s)) } catch (e) { rej(new Error(s.slice(0, 200))) } })
  }).on('error', rej)
})

;(async () => {
  const targets = await getJSON('/json/list')
  const t = targets.find((x) => x.type === 'page')
  if (!t) throw new Error('no page target')
  console.log('target:', t.url || '(空)', '| title:', t.title)
  const ws = new WS(t.webSocketDebuggerUrl, { perMessageDeflate: false, maxPayload: 512 * 1024 * 1024 })
  let id = 0
  const pending = new Map()
  ws.on('message', (m) => { const j = JSON.parse(m); if (j.id && pending.has(j.id)) { pending.get(j.id)(j); pending.delete(j.id) } })
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })) })
  await new Promise((r) => ws.on('open', r))
  const r = await Promise.race([
    send('Runtime.evaluate', { expression: EXPR, returnByValue: true, awaitPromise: false, timeout: MS }),
    new Promise((res) => setTimeout(() => res({ DEADLOCK: true }), MS + 4000))
  ])
  if (r.DEADLOCK) console.log('★ 主线程无响应（evaluate 请求被吞）——渲染进程卡死或已崩溃')
  else if (r.result && r.result.exceptionDetails) console.log('EXCEPTION:', JSON.stringify(r.result.exceptionDetails).slice(0, 600))
  else console.log('VALUE:', JSON.stringify(r.result && r.result.result && r.result.result.value).slice(0, 2000))
  process.exit(0)
})().catch((e) => { console.log('ERR', e.message); process.exit(1) })
