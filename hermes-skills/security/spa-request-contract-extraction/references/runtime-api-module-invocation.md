# 运行时接管: 在活页面里调用目标自己的 API 模块

适用: 目标 SPA 的请求参数/请求体加密, 且叠着 WAF 令牌链(响应也可能加密) ⇒ 本地复现加密的性价比极低。
做法: 让**目标自己的代码**替你加密、挂令牌、解密响应, 你只负责给参数、读明文。

## 1. 钩子(必须在文档加载前注入)

```python
HOOK = r"""(()=>{ if(window.__H) return 1; window.__H=1; window.__LOG=[];
  const op=XMLHttpRequest.prototype.open, ss=XMLHttpRequest.prototype.send, oo=XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open=function(m,u){ this.__m=m; this.__u=String(u); this.__hd={}; return op.apply(this,arguments); };
  XMLHttpRequest.prototype.setRequestHeader=function(k,v){ try{ if(this.__hd) this.__hd[String(k)]=String(v); }catch(e){} return oo.apply(this,arguments); };
  XMLHttpRequest.prototype.send=function(b){ const s=this;
    try{ if(s.__u && s.__u.indexOf('/app')>=0) window.__LOG.push({m:s.__m,u:s.__u,b:(typeof b==='string'?b:null),hd:s.__hd||{}}); }catch(e){}
    return ss.apply(this,arguments); };
  return 1; })()"""
t.send("Page.addScriptToEvaluateOnNewDocument", source=HOOK)
t.send("Page.reload")
```

- `setRequestHeader` **先于** `send` ⇒ 头必须挂在 XHR 对象上, 在 `send` 里一起落日志。
- 只钩 `fetch` 会得到"零业务请求"; axios 走 XHR。
- 重载后等 `document.readyState==='complete'` **且** 已捕获条数 > 0, 再驱动路由触发懒加载请求。

## 2. 拿到 API 模块并反查导出名

```js
(async()=>{ try{
  const urls = performance.getEntriesByType('resource').map(r=>r.name).filter(n=>/\.js(\?|$)/.test(n));
  for(const u of urls){ try{ const m = await import(u);
      if(m && m.e && m.J && Object.keys(m).length>10){ window.__A=m; window.__AU=u; break; } }catch(e){} }
  window.__R = window.__A ? ('API:'+window.__AU) : 'NOAPI'; }catch(e){ window.__R='EX:'+String(e); } })()
```

- 探测条件用"特征导出"(改成本目标实际存在的两三个导出名), 别只看键数。
- 模块路径常在**根** `/js/index-<hash>.js`; 相对路径 import 会失败。
- 导出映射(本地即可做, 一次拿全):
  ```bash
tail -c 3000 index-<hash>.js | tr ',' '\n' | grep -oE "[A-Za-z0-9_$]{1,4} as [A-Za-z0-9_$]+"
  ```
  形如 `cn as J` = addAgent, `pn as K` = edMer, `nn as E` = unlock ⇒ `await window.__A.J({...})`。
- 页面 chunk 的 `import{ J as de, H as fe } from "./index-<hash>.js"` 直接告诉你**哪个压缩名 = 哪个端点**(`de` 被当 addAgent 调、`fe` 当 hbconfig 调)。

## 3. 调用包装(轮询式, 兼容不支持 awaitPromise 的 CDP)

```python
def call(label, expr, wait=16):
    t.ev("window.__R='PENDING'; 1")
    t.ev("(async()=>{ try{ const r = await (%s); window.__R='OK|'+JSON.stringify(r).slice(0,4000); }"
         "catch(e){ window.__R='ERR|'+String((e&&(e.message||e.msg))||e).slice(0,400); } })()" % expr)
    for _ in range(int(wait/0.6)+5):
        t.pump(0.6)
        x = t.ev("window.__R")
        if x and x != "PENDING": break
        time.sleep(0.25)
    return x
```

**先跑控制组**(一个已知只读端点, 断言 200 + 有 data); 控制组不过 ⇒ 本轮全部作废, 不许解读。

## 4. 读取顺序(把"零副作用"榨干)

1. 配置/费率/阈值类: 这些就是报告材料(保证金门槛、费率、产品表、地区表)。
2. 列表/位置/收益类: 业务形态与技术栈佐证。
3. 写入类: 一律先**零写入探闸**——字段补全、把 2FA 码留空或填 `000000`。
   - 回「请输入谷歌验证器动态码」⇒ 2FA 是硬闸, 且**本账号已启用**(前端仅在 `hasGA` 为真时才拼 `googleCode`)。
   - 回「余额不足/保证金」⇒ 资金闸, 顺序在 2FA 之后。
   - 回「xxx不能为空」⇒ 描述字段仍不全, 回第 2 节读调用点。

## 5. 懒加载 chunk 全量落盘(表单字段只在页面 chunk 里)

```python
for h in ["/路由A", "/路由B", "/路由C"]:      # 逐路由导航, 触发懒加载
    t.ev("(()=>{location.hash='#%s';return 1})()" % h); time.sleep(2.5)
urls = json.loads(t.ev("JSON.stringify(performance.getEntriesByType('resource').map(r=>r.name).filter(n=>/\.js/.test(n)))") or "[]")
# 页内 fetch 每一条 → 文本落盘 → 本地 grep 关键词(中文表单标签/字段名)
```

- 页内 `fetch` 同源无 CORS 问题; 逐条 fetch 后**先判关键词再落盘**, 别把 60+ 个 chunk 全写盘再筛(浪费且易把无关文件混进情报)。
- 表单字段名的权威来源就是这个页面 chunk 的 setup 里那一句 `const a=l({...})`。
- 提交函数形如 `const ae={...a.value, ...(i.value?{googleCode:u}:{})}; g=await de(ae)` ⇒ **同时给出字段名、条件 2FA、成功判据(`code==200`)、成功后的副作用(localStorage 键 + 事件名)**。

## 6. 写入前的自律

- 真实写入(建号/改密/加余额)前先向用户确认一次, 即使已获「允许写入」的泛授权——**新建账号类写入与"偏好无痕"冲突**, 由用户裁决。
- 探针一律选"必然被校验拒绝"的组合(缺 2FA 码、格式非法), 保证零落库。
