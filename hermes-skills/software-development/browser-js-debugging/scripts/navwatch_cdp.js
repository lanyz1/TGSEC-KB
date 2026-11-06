// navwatch_cdp.js —— 双层导航监视器（浏览器层 Target.* + 页面层 frameNavigated/frameRequestedNavigation）
//
// 解决什么问题：现象是「页面卡死」——--dump-dom 超时、Debugger.pause 无响应、evaluate 全 undefined。
//   真因往往是**启动期整页重载风暴**（JS 每渲染一次就发一次导航），而非主线程阻塞。两者外部读数一样。
//   唯一判据 = 「请求的导航数 vs 实际提交的导航数」。
//   frameRequestedNavigation.reason 直接指认发射源：
//     reload            = location.reload() / history.go(0) / router.go(0)
//     scriptInitiated   = location.href=… / pushState
//     formSubmissionGet = 表单提交 / metaTag = meta refresh
//
// 为何要双层：页面层事件随渲染进程一起死，线索就断了；浏览器层 Target.* 即使渲染进程崩掉也继续报
//   （targetInfo.url 就是页面真实 URL）⇒ 风暴中的读数不会丢。
//
// 用法:  node navwatch_cdp.js --port 9222 --nav http://127.0.0.1:4173/ --wait 15000
//        node navwatch_cdp.js --port 9222 --wait 15000          # 不导航，只监视在跑的页面
// 依赖:  ws（优先 $WS_PATH 指向独立 scratch 工程的 node_modules；Node 22+ 无 ws 时回退全局 WebSocket）
const http = require('http')

let WS
let usingGlobalWS = false
let SOCK = null   // 模块级持有连接：finish() 定义在 IIFE 外，拿不到块级 ws
try { WS = require(process.env.WS_PATH || 'ws') } catch (e) {
  usingGlobalWS = true
  const G = globalThis.WebSocket
  WS = class {                       // 把全局 WebSocket 适配成 ws 的接口（addListener/removeListener/on）
    constructor(u) { this._w = new G(u); this._w.addEventListener('message', ev => this._emit('message', ev.data)) }
    addListener(t, fn) { (this._h ||= {})[t] = (this._h[t] || []).concat(fn) }
    removeListener(t, fn) { if (this._h?.[t]) this._h[t] = this._h[t].filter(f => f !== fn) }
    _emit(t, d) { (this._h?.[t] || []).forEach(f => f(d)) }
    send(s) { this._w.send(s) }
    close() { try { this._w.close() } catch (_) {} }
  }
}

const argv = process.argv.slice(2)
const arg = (n, d) => { const i = argv.indexOf(n); return i > -1 ? argv[i + 1] : d }
const PORT = arg('--port', '9222')
const NAV = arg('--nav', null)
const WAIT = parseInt(arg('--wait', '15000'), 10)

const httpGet = (p) => new Promise((res, rej) => {
  const rq = http.get({ host: '127.0.0.1', port: PORT, path: p, timeout: 5000 }, r => {
    let s = ''; r.on('data', d => s += d); r.on('end', () => res(s))
  })
  rq.on('error', rej); rq.on('timeout', () => rq.destroy(new Error('timeout')))
})

const t0 = Date.now()
const ts = () => '+' + ((Date.now() - t0) / 1000).toFixed(3) + 's'
const say = (tag, msg) => console.log(`${ts()} [${tag}] ${msg}`)

const stats = { requested: 0, committed: 0, byReason: {}, byUrl: {} }

;(async () => {
  const ver = JSON.parse(await httpGet('/json/version'))
  const ws = SOCK = new WS(ver.webSocketDebuggerUrl)
  let id = 0
  const send = (method, params = {}, sessionId) => new Promise(r => {
    const i = ++id
    const h = (m) => { const j = JSON.parse(m); if (j.id === i) { ws.removeListener('message', h); r(j) } }
    ws.addListener('message', h)
    ws.send(JSON.stringify({ id: i, method, params, ...(sessionId ? { sessionId } : {}) }))
  })

  await new Promise(r => ws.addListener('open', r))
  const targets = JSON.parse(await httpGet('/json/list')).filter(x => x.type === 'page')
  const page = targets[0]
  if (!page) { console.log('★ 没有 page target（浏览器可能已退出）'); return finish(1) }
  say('init', `page target = ${page.url}`)

  ws.addListener('message', (raw) => {
    let m; try { m = JSON.parse(raw) } catch (_) { return }
    const p = m.params || {}
    switch (m.method) {
      case 'Target.targetCreated': say('targetCreated', `${p.targetInfo?.type} | ${(p.targetInfo?.url || '').slice(0, 120)}`); break
      case 'Target.targetDestroyed': say('targetDestroyed', `${p.targetId}`); break
      case 'Target.targetInfoChanged': say('targetInfoChanged', `${p.targetInfo?.type} | ${(p.targetInfo?.url || '').slice(0, 120)} | ${p.targetInfo?.attached ? 'attached' : ''}`); break
      case 'Target.targetCrashed': say('targetCrashed', `${p.targetId} | status=${p.status} errorCode=${p.errorCode}`); break
      case 'Page.frameNavigated': say('frameNavigated', `${p.frame?.url}`); stats.committed++; break
      case 'Page.frameRequestedNavigation': {
        const r = p.reason || 'other', u = p.url || ''
        stats.requested++; stats.byReason[r] = (stats.byReason[r] || 0) + 1; stats.byUrl[u] = (stats.byUrl[u] || 0) + 1
        say('navRequested', `${u} | reason= ${r}`); break
      }
      case 'Page.loadEventFired': say('loadEventFired', ''); break
      case 'Page.javascriptDialogOpening': say('dialog', `${p.type} ${JSON.stringify(p.message).slice(0, 120)}`); break
      case 'Runtime.exceptionThrown': {
        const d = p.exceptionDetails || {}
        say('EXC', `${d.text || ''} @ ${(d.url || '')}:${d.lineNumber} ${(d.exception?.description || '').split('\n')[0]}`); break
      }
      case 'Runtime.consoleAPICalled': {
        const lv = p.type
        if (lv === 'error' || lv === 'warning') say('console.' + lv, (p.args || []).map(a => a.value ?? a.description ?? '').join(' ').slice(0, 200))
        break
      }
      case 'Log.entryAdded': {
        const e = p.entry || {}
        if (e.level === 'error') say('log.error', `${e.text || ''} | ${(e.url || '').slice(0, 120)}`)
        break
      }
    }
  })

  await send('Target.setDiscoverTargets', { discover: true })
  const att = await send('Target.attachToTarget', { targetId: page.id, flatten: true })
  const sess = att.result && att.result.sessionId
  if (!sess) { console.log('★ attachToTarget 失败：' + JSON.stringify(att.error || att).slice(0, 200)) }
  for (const d of ['Page', 'Runtime', 'Log']) await send(`${d}.enable`, {}, sess)

  if (NAV) { say('nav', `Page.navigate → ${NAV}`); await send('Page.navigate', { url: NAV }, sess) }

  setTimeout(finish, WAIT)
})().catch(e => { console.log('★ navwatch 失败: ' + e.message); process.exitCode = 1; setTimeout(() => process.exit(process.exitCode || 0), 400) })

function finish(code) {
  console.log('\n=== 导航统计 ===')
  console.log(`请求导航(requested)=${stats.requested}  提交导航(frameNavigated)=${stats.committed}`)
  console.log('按 reason: ' + JSON.stringify(stats.byReason))
  console.log('按 URL: ' + JSON.stringify(stats.byUrl))
  const reload = stats.byReason.reload || 0
  if (reload >= 3 && stats.committed <= reload) {
    console.log('★★ 判为「启动期重载风暴」：JS 在渲染期反复发起导航（请求数 ≫ 提交数）')
    console.log('   下一步：搜模板/脚本里的属性形式处理函数 `:onXxx="fn()"` 与路由守卫自环；先别信 dump/evaluate 的读数')
  } else if (stats.requested === 0 && stats.committed >= 1) {
    console.log('✓ 无重载风暴（未捕获到导航请求）')
  }
  try { SOCK && SOCK.close() } catch (_) {}
  setTimeout(() => process.exit(code || 0), 400)   // ★ 紧跟 ws.close() 的 exit 会截断管道输出
}
