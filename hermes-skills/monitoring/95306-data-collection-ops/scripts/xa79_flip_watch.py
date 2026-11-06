# -*- coding: utf-8 -*-
# 部署于主服 /opt/v6/xa79_flip_watch.py (cron */15min, flock -n /tmp/xa79_flip.lock)
# 作用: 盯 XA79 项目状态; 一旦 结果公告发布/status≠31 → 日切收割 b580 全窗, 命中日整日落盘
# 通用化: 换 PID/OUTD/TGT 可复用于任何"31态卡住"项目
import json,ssl,urllib.request,time,os,datetime
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"
API="https://cg.95306.cn/proxy/dataplatform/api/findList"
PID="3a5a0784-7bd6-4ce5-a855-dc56c23026fe"
TGT=('3a5a0784','6fc6c9a4','f40eed84','94ee82f2','dcd27e6c','90e237f8','16611220','5beb3fda','6913326d')
LOG="/tmp/xa79_flip.log"; OUTD="/data_raw/xa79_flip"; LAST=OUTD+"/last_attempt"
def call(fid,params=None,pn=1,ps=100,tmo=50):
    body={"funcId":fid,"appId":"system","pageNum":pn,"pageSize":ps,"params":params or [],"condition":""}
    req=urllib.request.Request(API,data=json.dumps(body).encode(),headers={"Content-Type":"application/json;charset=UTF-8","User-Agent":UA})
    return urllib.request.urlopen(req,timeout=tmo,context=ctx).read().decode('utf-8','replace')
def log(s):
    line=time.strftime('[%m-%d %H:%M] ')+s
    print(line,flush=True)
    try: open(LOG,'a').write(line+"\n")
    except Exception: pass
def harvest():
    if os.path.exists(OUTD+"/DONE"): log("harvest already done"); return
    try:
        if os.path.exists(LAST):
            d0=datetime.datetime.strptime(open(LAST).read().strip()[:16],'%Y-%m-%d %H:%M')
            if (datetime.datetime.utcnow()-d0).total_seconds()<7200: log("retry gate <2h"); return
    except Exception: pass
    os.makedirs(OUTD,exist_ok=True)
    open(LAST,'w').write(time.strftime('%Y-%m-%d %H:%M',time.gmtime()))
    stamp=time.strftime('%m%d_%H%M'); tot=0; hitday=0
    d=datetime.date(2026,8,20); end=datetime.date(2026,10,31)
    while d<=end:
        a=d.strftime('%Y-%m-%d')+" 00:00:00"; b=d.strftime('%Y-%m-%d')+" 23:59:59"
        p=[{"key":"start_time","value":a},{"key":"end_time","value":b}]
        pn=1; day=[]
        while True:
            t=call("bid_package_bidder_business23",p,pn=pn,ps=100)
            if t.startswith("ERR"): log("ERR %s p%d"%(d,pn)); break
            try: j=json.loads(t)
            except Exception: break
            day+=j.get("data") or []; ts=j.get("totalSize") or 0
            if pn*100>=ts or pn>=60: break
            pn+=1
        tot+=len(day); blob=json.dumps(day,ensure_ascii=False)
        found=[k for k in TGT if k in blob]
        if found:
            fn="%s/b580_%s_%s.json"%(OUTD,stamp,d.strftime('%m%d'))
            open(fn,'w').write(blob); hitday+=1
            log("DAY HIT %s rows=%d %s"%(d,len(day),found))
        d+=datetime.timedelta(days=1)
    if hitday>0:
        open(OUTD+"/DONE",'w').write(stamp); log("harvest done total=%d hitdays=%d"%(tot,hitday))
    else:
        log("harvest done total=%d NO HITS (retry in 2h)"%tot)
def main():
    try:
        t=call("startingbiddetailspackage",[{"key":"id","value":PID}],ps=1)
        j=json.loads(t); rows=j.get("data") or []
        st=rows[0].get("status") if rows else "?"; jg=rows[0].get("jieguo_pub_time") if rows else "?"
        log("status=%s jieguo=%s"%(st,jg))
        if st!='31' or (jg and jg!='-'): log("FLIP DETECTED -> harvest"); harvest()
    except Exception as e: log("ERR %r"%e)
main()
