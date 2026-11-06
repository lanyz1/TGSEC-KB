## 第 1 步: 空间测绘语法找 Bot 后台(搜代替扫)

**Shodan**(shodan.io,注册免费额度):
```
http.title:"bot" port:443
http.title:"telegram" http.html:"bot"
http.title:"panel" http.html:"telegram"
http.html:"bot_token"
http.title:"dashboard" http.html:"/bot"
```

**Fofa**(fofa.info,注册即用):
```
title="Bot" && body="telegram"
body="bot_token" && port="443"
title="Dashboard" && body="bot" && country="US"
header="nginx" && body="telegram_bot"
body="bot" && port="8080"        # 非标准端口防护更弱, 弱口令概率高
```

