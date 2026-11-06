# 浏览器驱动取证 harness（录制器 / 框架实例内省 / 真路由）

用于「手工复刻请求恒回同一笼统码」时的取证：让页面自己把请求发出去，再把**真 URL + 真参数 + 真结果**录下来。

## 1. XHR + fetch 录制器（必须加载前注入）

```js
// 先 Page.addScriptToEvaluateOnNewDocument(source=<本 IIFE>) 再 reload；只打补丁不刷新会在下次导航全丢
(() => {
  const L = []; window.__L = L;
  const O = XMLHttpRequest.prototype.open, S = XMLHttpRequest.prototype.send, H = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function (m, u) { this.__m = m; this.__u = u; this.__hd = {}; return O.apply(this, arguments); };
  XMLHttpRequest.prototype.setRequestHeader = function (k, v) { try { this.__hd[k] = v; } catch (e) {} return H.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (b) { try { L.push({ t: 'xhr', m: this.__m, u: this.__u, hd: this.__hd, b: typeof b === 'string' ? b : '' }); } catch (e) {} return S.apply(this, arguments); };
  const f = window.fetch;
  window.fetch = function (i, o) { try { L.push({ t: 'fetch', u: typeof i === 'string' ? i : (i && i.url), hd: (o && o.headers) || {}, b: (o && o.body) || '' }); } catch (e) {} return f.apply(this, arguments); };
})();
```

- 读取：`JSON.stringify(window.__L)`；**每批前 `window.__L.length = 0` 清空**。
- ★ 头必须在内层 `setRequestHeader` 里收：只在 `send` 里记 ⇒ 录到的模板**头全空**，照抄后整齐被拒而看不出原因。
- ★ 只钩 `fetch` 会得到「零业务请求」（axios 走 XHR adapter / 自研 XHR）⇒ 两个都钩。

## 2. 框架实例内省（Vue；React 看 fiber / 全局 store）

```js
function walk(vm, d, out) {
  if (!vm || d > 5 || out.length > 60) return out;
  out.push({
    n: (vm.$options && (vm.$options.name || vm.$options.__file)) || '?',
    data: Object.keys(vm._data || {}),
    methods: Object.keys((vm.$options && vm.$options.methods) || {}),
  });
  (vm.$children || []).forEach(c => walk(c, d + 1, out));
  return out;
}
walk(document.querySelector('#app').__vue__, 0, []);
```

- **一次性挑战产物**（验证码 ticket / randstr / 握手 token）通常就在组件 `_data` 的某个 form 对象里 ⇒ 深度 dump 一次即可读到，不必解析网络响应。
- **可以直接调用站点自己的方法**：`vm.$options.methods.<name>.call(vm, ...)` ⇒ 由站点代码去发请求（含它自己的加密/头/令牌链）。
- **路由表**：`vm.$router.options.routes` / `vm.$router.getRoutes()`，递归 flatten `children`；一次拿到全站页面清单（= 攻击面地图：代理面 / 资金面 / 安全面 / 业务面）。
- ★ 组件里的弹窗切换方法（`$emit('changeDlg', 2)` 之类）常**不改 DOM**（子组件不实例化）⇒ 别在方法上耗轮次，改用真路由。

## 3. 真路由导航

`nav('https://<host>/#/registry?upcode=<自己的邀请码>')` + 等待渲染 ⇒ 读 `input` 的 placeholder 与按钮文本确认是目标页。
带参数的入口路由（`?upcode=` / `?hbid=` / `?ref=`）常同时是**账号池的开关**：参数可控 ⇒ 可自建下级账号。

## 4. 驱动到提交（checklist）

1. 填表（字段名照 placeholder 读，不照源码猜）；
2. 勾人机校验框 ⇒ 弹窗出现；
3. 处理挑战（滑块走真鼠标拖拽）；
4. 点**站点自己的提交按钮**（不是自造请求）；
5. 读 `window.__L` 最后一条 = 真 URL + 真 query + 真头；
6. 响应里的会话令牌（`suid`/`token`/`uid`）立刻落盘，下一步直接复用。

## 5. 判读纪律

- **录音优先于源码**：真请求常带源码 `data.form` 里不存在的伴随字段（实测真 URL 多一个源码 form 没有的确认字段）⇒ 契约以录音为准。
- 同一句笼统码先分两相：**缺凭证**（补挑战产物）× **必须页面自发**（改 UI 驱动）。两个方向的动作完全不同，别混着猜。
- 一次性的东西（ticket/挑战产物/session）**取到即用**：跨轮复用一律假阴性。
- 录制器本身也会被风控看（多次重载同一会话）⇒ 一次到位，别反复刷。
