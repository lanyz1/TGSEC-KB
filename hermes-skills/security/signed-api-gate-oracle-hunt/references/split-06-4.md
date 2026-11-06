## 4. 兄弟前端改判(签名打不动时的战略转向)
- 一套前端的登录链在 API 主机上**全 404** ⇒ 该前端有独立后端,**是另一台主机**,不是路径写错。用候选域名族探测定位(前缀方向:`al-`、`api-`、`mobile-`、`-h5`、`h5-`、`wap-`、`applet-`)。
- 找到后先重跑登录链:若同业务的另一套 API(`/api/oauth/*`、`/api/v2/*`)免签,直接在该面上拿会话,回头再用会话打原来的签名面。
- **多套 SPA 并存**(`/h5/` 与 `/h5-v2/` 是两套不同应用,各有自己的 app.js)。权威契约 = 各自 `js/app.*.js` 里的 route 表 + **API 常量对象**;从里面能一次抽出几百条路径(含 `?` 后的参数名)。
- **302 的 Location 会暴露新应用**:某端点把你 302 到 `/h5-v2/<route>?<参数>` ⇒ 该 base 是新前端,立刻拉它的 `index.html` → app.js → 重抽 API 常量。
- 抽取命令(先落盘再 grep,别 inline):
```bash
curl -sk -o /root/t/app.js "https://<host>/<base>/js/app.<hash>.js"
grep -o 'prototype\.[A-Za-z0-9_]*=function([^)]*)' /root/t/app.js | head -60   # 方法签名=契约
grep -o '"/[a-zA-Z0-9/_{}.-]*"' /root/t/app.js | sort -u | head -200        # API 常量
```

