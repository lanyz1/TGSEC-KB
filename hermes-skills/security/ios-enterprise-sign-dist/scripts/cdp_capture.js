#!/usr/bin/env node
/*
 * 通过 CDP 打开页面、收集全部网络请求、可选点击文本匹配的元素。
 * 前置: chromium --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
 *         --remote-debugging-port=9222 --user-data-dir=/tmp/cdp-prof \
 *         --user-agent="<iPhone UA>" about:blank
 * 用法: node cdp_capture.js <url> [clickTextRegex] [waitSeconds]
 * 输出: 全部 REQ/RES 事件(URL 含 k/cmduuid/ipa 等关键参数)
 */
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const url = process.argv[2];
  const clickText = process.argv[3] || '';
  const waitS = parseInt(process.argv[4] || '12', 10);
  if (!url) { console.error('usage: node cdp_capture.js <url> [clickTextRegex] [waitSeconds]'); process.exit(1); }

  const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
  const page = list.find(t => t.type === 'page');
  if (!page) { console.error('no page target'); process.exit(1); }

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const events = [];
  const send = (method, params = {}) => new Promise(res => {
    const i = ++id;
    pending.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result || m.error); pending.delete(m.id); }
    else if (m.method === 'Network.requestWillBeSent') {
      events.push(['REQ', m.params.request.method, m.params.request.url, (m.params.request.postData || '').slice(0, 300)]);
    } else if (m.method === 'Network.responseReceived') {
      events.push(['RES', m.params.response.status, m.params.response.url]);
    }
  };
  await new Promise(r => { ws.onopen = r; });
  await send('Network.enable');
  await send('Page.enable');
  await send('Page.navigate', { url });
  await sleep(waitS * 1000);

  if (clickText) {
    const r = await send('Runtime.evaluate', {
      expression: `(() => {
        const rx = new RegExp(${JSON.stringify(clickText)});
        const els = [...document.querySelectorAll('button,div,span,a')];
        const el = els.find(e => rx.test((e.innerText || '').trim()) && e.children.length === 0);
        if (el) { el.click(); return 'CLICKED: ' + el.innerText; }
        return 'NOT FOUND';
      })()`,
      returnByValue: true
    });
    console.log('CLICK:', r.result && r.result.value);
    await sleep(waitS * 1000);
  }

  console.log('=== NETWORK EVENTS ===');
  for (const e of events) console.log(e.join(' | '));
  ws.close();
}

main().catch(e => { console.error('ERR', e.message); process.exit(1); });
