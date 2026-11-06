"""看图工具 - 统一走 API 调用(会话内约定,用户 2026-08-04 定)
用法:
  python vision-api.py <图片路径> [问题]
  例: python vision-api.py C:\\x.png "描述这张截图里的按钮"
key 自动从 ~/.cc-switch/cc-switch.db 读取(My Codex222),不硬编码不显示。
"""
import sys, os, json, sqlite3, base64, urllib.request

def get_key():
    db = os.path.expanduser('~/.cc-switch/cc-switch.db')
    con = sqlite3.connect(db)
    cur = con.cursor()
    rows = cur.execute('SELECT name, settings_config FROM providers').fetchall()
    for name, cfg in rows:
        try:
            d = json.loads(cfg) if cfg else {}
        except Exception:
            continue
        if name == 'My Codex222' and 'auth' in d and isinstance(d['auth'], dict):
            return d['auth'].get('OPENAI_API_KEY')
    return None

def main():
    if len(sys.argv) < 2:
        print('用法: python vision-api.py <图片路径> [问题]')
        sys.exit(1)
    img_path = sys.argv[1]
    question = sys.argv[2] if len(sys.argv) > 2 else '请描述这张图片的内容'
    if not os.path.exists(img_path):
        print('IMG NOT FOUND:', img_path)
        sys.exit(1)
    key = get_key()
    if not key:
        print('KEY_NOT_FOUND')
        sys.exit(1)
    with open(img_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    body = json.dumps({
        'model': 'gpt-5.5',
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': question},
            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + b64}}
        ]}]
    }).encode()
    req = urllib.request.Request(
        'https://api.aisz.mom/v1/chat/completions',
        data=body,
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
    )
    try:
        r = urllib.request.urlopen(req, timeout=120)
        resp = json.loads(r.read())
        print(resp['choices'][0]['message']['content'])
    except Exception as e:
        print('VISION FAIL:', str(e)[:300])
        sys.exit(1)

if __name__ == '__main__':
    main()
