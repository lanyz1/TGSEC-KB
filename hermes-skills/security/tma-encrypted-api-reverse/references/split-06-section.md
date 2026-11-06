## 反侦察/蜜罐识别
- `/admin`、`/dashboard`、`/console` 返回**同一份小体积假登录页**(sha 相同)、提交跳 `/gotcha.html`、零 assets、另有 `/honeypot-whoami` 回显访客 IP → 全是**反扫描诱饵**,别在登录爆破上耗时。
- 所有打目标的流量走跳板机;本机只留 TG API(走本地代理)。

