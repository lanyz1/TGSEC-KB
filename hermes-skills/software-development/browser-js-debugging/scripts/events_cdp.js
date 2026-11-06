// events_cdp.js —— 只收 CDP 事件、绝不调用 Runtime.evaluate
//
// 用途：页面主线程被**同步阻塞**（原生对话框 alert/confirm/print、同步 XHR 等）或饥饿时，
//   evaluate 会永远排队、Debugger.pause 也不响应；但事件流仍会到达。
//   本脚本做 Page.navigate 并原样打印一段时间内收到的全部事件（含 javascriptDialogOpening、
//   consoleAPICalled、exceptionThrown、Log.entryAdded），是这类卡死的唯一可读窗口。
//
// 依赖：ws（装到独立 scratch 工程，用 WS_PATH 指过去）
// 用法：WS_PATH=<scratch>/node_modules/ws node events_cdp.js "<url>" [--port 9222] [--wait 20000] [--auto-dismiss]
//   --auto-dismiss  自动接受原生对话框（确认「对话框阻塞」就是根因）
const http = require('http')
const WS = require(process.env.WS_PATH || 'ws')
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d }
const URL_ = process.argv[2] || 'about:blank'
const PORT = Number(arg('port', 9222))
const WAIT = Number(arg('wait', 20000))
const DISMISS = process.argv.includes('--auto-dismiss')

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
  const ws = new WS(t.webSocketDebuggerUrl, { perMessageDeflate: false, maxPayload: 512 * 1024 * 1024 })
  let id = 0
  const pending = new Map()
  let dialogs = 0
  ws.on('message', (m) => {
    const msg = JSON.parse(m)
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); return }
    const p = msg.params || {}
    switch (msg.method) {
      case 'Page.javascriptDialogOpening':
        dialogs++
        console.log('[DIALOG]', p.type, '|', JSON.stringify(p.message).slice(0, 200), '| url:', p.url)
        if (DISMISS) send('Page.handleJavaScriptDialog', { accept: true })
        break
      case 'Runtime.consoleAPICalled':
        console.log('[console.' + p.type + ']', (p.args || []).map((a) => String((a && (a.value !== undefined ? a.value : a.description)) || a.type).slice(0, 200)).join(' ').slice(0, 300))
        break
      case 'Runtime.exceptionThrown': {
        const d = p.exceptionDetails || {}
        console.log('[EXCEPTION]', ((d.exception && d.exception.description) || d.text || '').replace(/\s+/g, ' ').slice(0, 400))
        break
      }
      case 'Log.entryAdded':
        console.log('[log.' + (p.entry && p.entry.level) + ']', ((p.entry && p.entry.text) || '').replace(/\s+/g, ' ').slice(0, 300))
        break
      case 'Page.frameNavigated':
      case 'Page.loadEventFired':
      case 'Page.domContentEventFired':
      case 'Inspector.targetCrashed':
      case 'Target.targetCrashed':
        console.log('[' + msg.method + ']', ((p.frame && p.frame.url) || '').slice(0, 100))
        break
      default:
        break
    }
  })
  function send(method, params = {}) { return new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })) }) }
  await new Promise((r) => ws.on('open', r))
  await send('Page.enable'); await send('Runtime.enable'); await send('Log.enable')
  await send('Page.navigate', { url: URL_ })
  console.log('--- events for', WAIT, 'ms ---')
  await new Promise((r) => setTimeout(r, WAIT))
  console.log('DIALOGS:', dialogs)
  ws.close(); process.exit(0)
})().catch((e) => { console.log('ERR', e.message); process.exit(1) })
