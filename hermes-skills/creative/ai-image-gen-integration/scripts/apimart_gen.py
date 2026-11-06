#!/usr/bin/env python3
"""APIMart 人像写真生成通用脚本:上传底图 -> 多模态描述 -> 多模型x场景 -> 轮询 -> 下载

用法:
  export APIMART_KEY=sk-...            # 或同目录放 .apimart_key 文件
  python3 apimart_gen.py photo.jpg                    # 1) 上传+多模态描述人物,写 photo_desc.txt
  python3 apimart_gen.py photo.jpg seaside,korean     # 2) 生成(场景名逗号分隔,写 SCENES 字典加场景)
输出:out/p_<scene>_<model>_<i>.png ;预览图 out_small/*.jpg
依赖:requests pillow ;本机需代理 127.0.0.1:10808(v2rayN)
"""
import requests, json, os, sys, time, glob
urllib3 = __import__("urllib3"); urllib3.disable_warnings()

BASE = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get("APIMART_KEY") or open(os.path.join(BASE, ".apimart_key")).read().strip()
PROXY = {"http": "http://127.0.0.1:10808", "https": "http://127.0.0.1:10808"}
API = "https://api.apimart.ai/v1"
H = {"Authorization": f"Bearer {KEY}"}
DESCRIBER = "gemini-2.5-flash-nothinking"   # 看图描述用;thinking 变体会吃光 max_tokens

SCENES = {}  # 场景名 -> 场景提示词,按业务添加
FACE_DESC = ""  # 从 photo_desc.txt 的 JSON 提炼,或用 --face 传

def upload(path):
    with open(path, "rb") as f:
        r = requests.post(f"{API}/uploads/images", headers=H, files={"file": f}, proxies=PROXY, timeout=60)
    d = r.json()
    return d.get("url") or (d.get("data") or {}).get("url")

def describe(url, prompt=None):
    """用多模态 LLM 看底图,返回文本(JSON 人物特征)"""
    prompt = prompt or ('仔细观察这张照片,用中文输出 JSON {"gender","age","face","hair","clothes","pose","background","style_hint"},'
                        '再另起一行写 100 字整体描述。')
    body = {"model": DESCRIBER, "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": url}}]}], "max_tokens": 900, "stream": False}
    r = requests.post(f"{API}/chat/completions", json=body, headers={**H, "Content-Type": "application/json"},
                      proxies=PROXY, timeout=180)
    return r.json()["choices"][0]["message"]["content"]

def submit(model, prompt, ref_url):
    """提交生图。注意:image_urls 必须是字符串数组,对象数组会报 unmarshal 错"""
    payload = {"model": model, "prompt": prompt, "size": "3:4", "n": 1,
               "image_urls": [ref_url]}
    r = requests.post(f"{API}/images/generations", json=payload,
                      headers={**H, "Content-Type": "application/json"}, proxies=PROXY, timeout=60)
    d = r.json()
    data = d.get("data")
    task_id = data[0].get("task_id") if isinstance(data, list) else data.get("task_id")
    if not task_id:
        raise RuntimeError(str(d)[:300])
    return task_id

def check(task_id):
    r = requests.get(f"{API}/tasks/{task_id}?language=zh", headers=H, proxies=PROXY, timeout=30)
    data = r.json().get("data", {})
    st = data.get("status")
    if st == "completed":
        urls = []
        for it in (data.get("result", {}).get("images", []) or []):
            u = it.get("url")
            urls.extend(u if isinstance(u, list) else [u])
        return {"state": "done", "urls": urls, "credits": data.get("credits_cost")}
    if st in ("failed", "error", "cancelled"):
        return {"state": "err", "err": str(data)[:200]}
    return {"state": "pending"}

def download(url, path):
    for proxy in (PROXY, None):
        try:
            r = requests.get(url, proxies=proxy, timeout=60)
            if r.status_code == 200:
                open(path, "wb").write(r.content)
                return True
        except Exception:
            pass
    return False

def make_previews():
    from PIL import Image
    os.makedirs(os.path.join(BASE, "out_small"), exist_ok=True)
    for f in glob.glob(os.path.join(BASE, "out", "*.png")):
        im = Image.open(f); im.thumbnail((700, 700))
        im.convert("RGB").save(os.path.join(BASE, "out_small", os.path.basename(f).replace(".png", ".jpg")), "JPEG", quality=85)

def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    photo = sys.argv[1]
    ref_url = upload(photo)
    print("IMG_URL:", ref_url)
    if len(sys.argv) < 3:
        txt = describe(ref_url)
        open(os.path.join(BASE, "photo_desc.txt"), "w", encoding="utf-8").write(txt)
        print(txt); return
    # 生成模式
    os.makedirs(os.path.join(BASE, "out"), exist_ok=True)
    scenes = [s for s in sys.argv[2].split(",") if s in SCENES]
    face = FACE_DESC or "参考照片中的人物"
    models = ["seedream-4-5", "seedream-5-0-pro", "gpt-image-2-official",
              "gemini-3.1-flash-image-preview", "qwen-image-3.0"]
    tasks = []
    for sc in scenes:
        for m in models:
            prompt = (f"参考照片中的是一位{face}。保持面部特征五官脸型发型完全一致、可辨识为同一人,"
                      f"置于场景:{SCENES[sc]}。真人实拍质感,不要动漫化。")
            try:
                tid = submit(m, prompt, ref_url)
                tasks.append({"m": m, "sc": sc, "id": tid, "t0": time.time()})
                print(f"ok {sc}/{m} {tid[:36]}", flush=True)
            except Exception as e:
                print(f"FAIL {sc}/{m} {e}", flush=True)
    print("polling...", flush=True)
    while tasks and time.time() - tasks[0]["t0"] < 400:
        nxt = []
        for t in tasks:
            res = check(t["id"])
            if res["state"] == "done":
                for i, u in enumerate(res["urls"]):
                    p = os.path.join(BASE, "out", f"p_{t['sc']}_{t['m']}_{i}.png")
                    print(("save ok " if download(u, p) else "save FAIL ") + p, flush=True)
            elif res["state"] == "err":
                print(f"ERR {t['sc']}/{t['m']} {res['err']}", flush=True)
            else:
                nxt.append(t)
        tasks = nxt
        if tasks:
            time.sleep(4)
    make_previews()

if __name__ == "__main__":
    main()
