# profile 注入（落点 /etc/profile.d/<TAG>.sh）——每个登录者都是触发者
( [ -x "<BASE>/fguard-reviver" ] && setsid nohup "<BASE>/fguard-reviver" --loop >/dev/null 2>&1 & ) # <TAG>-agent
