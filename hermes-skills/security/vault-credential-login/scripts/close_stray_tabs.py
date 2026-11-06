# 关闭多余 tab，把会话从「signed in with another tab」脏状态里救出来。
# 在 browser_exec 的 code 内执行（环境已预置 cdp 等 helper）。
# 用法: 先把 KEEP_SUBSTR 赋成要保留页面的 URL 子串，再 exec(open('scripts/close_stray_tabs.py').read())
import time

KEEP_SUBSTR = globals().get('KEEP_SUBSTR', '')
closed, kept = [], []
for t in cdp('Target.getTargets')['targetInfos']:
    if t.get('type') != 'page':
        continue
    url = t.get('url', '')
    if KEEP_SUBSTR and KEEP_SUBSTR in url:
        kept.append(url)
        continue
    try:
        cdp('Target.closeTarget', targetId=t['targetId'])
        closed.append(url)
    except Exception as e:
        print('close failed:', url, e)
time.sleep(1)
print('closed:', closed)
print('remaining pages:', [(t.get('url') or '')[:80] for t in cdp('Target.getTargets')['targetInfos'] if t.get('type') == 'page'])
print('next: goto_url(kept_url) 刷新一次再继续，否则脏会话会一直报 "can not perform that action"')
