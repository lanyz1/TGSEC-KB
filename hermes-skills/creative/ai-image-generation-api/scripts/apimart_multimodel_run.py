#!/usr/bin/env python3
"""APIMart 多模型生图一条龙:上传参考图 -> 并行提交 -> 统一轮询 -> 下载落盘。

用法:
    python apimart_multimodel_run.py <scene> [models...]
    python apimart_multimodel_run.py --idphoto          # 证件照四连(白底西装/蓝底/红底/白底衬衫)
    python apimart_multimodel_run.py --describe <photo>  # 用多模态 chat 看图并输出人物特征 JSON

依赖: pip install requests pillow ; 本机需 v2rayN 代理 127.0.0.1:10808
约定: 同目录 .apimart_key 存 key;ref_urls.txt 每行一个参考图 URL
"""
import requests, json, os, sys, time
urllib3 = __import__("urllib3"); urllib3.disable_warnings()

BASE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(BASE, ".apimart_key")).read().strip()
PROXY = {"http": "http://127.0.0.1:10808", "https": "http://127.0.0.1:10808"}
API = "https://api.apimart.ai/v1"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
OUT = os.path.join(BASE, "out"); os.makedirs(OUT, exist_ok=True)

FACE = "瓜子脸、大眼睛、双眼皮、高鼻梁的年轻中国女性,深棕色长直发中分"  # 按参考图改
KEEP = ("请保持她的面部特征、五官、脸型、发型完全一致、可清晰辨识为同一人,"
        "头部必须随身体一起转向,不要把脸扭回正面。真人实拍质感,不要动漫化,不要改变五官比例和脸型。")

SCENES = {
    "seaside": "白色轻纱长裙站在海边礁石上,海风轻拂发丝,日落暖金色逆光,全身构图,电影感色调",
    "korean":  "米色针织开衫搭配白色连衣裙,坐在ins风咖啡店窗边捧咖啡杯,柔和窗光,韩系奶油色调,半身构图",
    "hanfu":   "浅色齐胸襦裙汉服,发髻配珍珠发簪,古风庭院竹林前执团扇,清晨薄雾,半身构图",
    "evening": "黑色修身缎面晚礼服,站在都市高层天台,身后城市夜景灯光虚化,时尚大片风格,半身构图",
    "office":  "米白色西装套装内搭白衬衫,站在写字楼落地窗前,明亮自然光,商务形象照,半身构图",
    "island":  "波西米亚白度假裙戴宽檐草帽,站热带海岛浅滩,碧海棕榈,全身构图,通透胶片色调",
}

IDPHOTO = {
    "id_white_suit":  ("纯白色", "深黑色西装外套内搭白色衬衫并系深色领带"),
    "id_blue_shirt":  ("纯蓝色", "白色衬衫并系深色领带"),
    "id_red_shirt":   ("纯红色", "白色衬衫并系深色领带"),
    "id_white_shirt": ("纯白色", "简洁白色衬衫"),
}

def upload(path):
    with open(path, "rb") as f:
        r = requests.post(f"{API}/uploads/images", headers={"Authorization": f"Bearer {KEY}"},
                          files={"file": f}, proxies=PROXY, timeout=90)
    return r.json().get("url")

def submit(model, prompt, size="3:4", refs=None, n=1):
    body = {"model": model, "prompt": prompt, "size": size, "n": n}
    if refs: body["image_urls"] = refs          # 必须字符串数组
    r = requests.post(f"{API}/images/generations", json=body, headers=H, proxies=PROXY, timeout=60)
    d = r.json(); data = d.get("data")
    tid = (data[0].get("task_id") if isinstance(data, list) else data.get("task_id")) if data else None
    return tid, (None if tid else str(d)[:220])

def check(tid):
    r = requests.get(f"{API}/tasks/{tid}?language=zh", headers=H, proxies=PROXY, timeout=30)
    data = r.json().get("data", {})
    st = data.get("status")
    if st == "completed":
        urls = []
        for it in (data.get("result", {}).get("images", []) or []):
            u = it.get("url"); urls += u if isinstance(u, list) else ([u] if u else [])
        return {"s": "done", "urls": urls}
    if st in ("failed", "error", "cancelled"):
        return {"s": "err", "err": f"{st} {data.get('error', {}).get('message', '')}"}
    return {"s": "pending"}

def download(url, path):
    for p in (PROXY, None):
        try:
            r = requests.get(url, proxies=p, timeout=60)
            if r.status_code == 200:
                open(path, "wb").write(r.content); return True
        except Exception: pass
    return False

def run(jobs, timeout=400):
    """jobs: {tag: (model, prompt, size, refs)}"""
    pend = {}
    for tag, (model, prompt, size, refs) in jobs.items():
        tid, err = submit(model, prompt, size, refs)
        if tid: pend[tid] = {"tag": tag, "t0": time.time()}; print("ok  ", tag, tid[:36], flush=True)
        else:   print("FAIL", tag, err, flush=True)
    done = {}
    while pend and time.time() - min(p["t0"] for p in pend.values()) < timeout:
        for tid in list(pend):
            res = check(tid)
            if res["s"] == "done":
                done[tid] = res; print("done", pend[tid]["tag"], f'{int(time.time()-pend[tid]["t0"])}s', flush=True)
                del pend[tid]
            elif res["s"] == "err":
                print("ERR ", pend[tid]["tag"], res["err"], flush=True); del pend[tid]
        if pend: time.sleep(4)
    for tid, res in done.items():
        for i, u in enumerate(res["urls"]):
            fn = os.path.join(OUT, f'{done[tid]["tag"]}_{i}.png')
            print("save", fn, download(u, fn), flush=True)

def describe(photo):
    url = upload(photo)
    print("IMG_URL:", url)
    q = ('请仔细观察这张照片并输出中文 JSON:{"gender":"","age":"","face":"脸型/五官/眼镜","hair":"",'
         '"angle":"拍摄角度","clothes":"","framing":"取景","light":"","bg":""} 然后一行100字整体描述。')
    body = {"model": "gemini-2.5-flash-nothinking", "stream": False, "max_tokens": 900,
            "messages": [{"role": "user", "content": [{"type": "text", "text": q},
                          {"type": "image_url", "image_url": {"url": url}}]}]}
    r = requests.post(f"{API}/chat/completions", json=body, headers=H, proxies=PROXY, timeout=180)
    txt = r.json()["choices"][0]["message"]["content"]
    print(txt); open(os.path.join(BASE, "photo_desc.txt"), "w", encoding="utf-8").write(txt)

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(0)
    if args[0] == "--describe":
        describe(args[1]); sys.exit(0)
    refs = [l.strip() for l in open(os.path.join(BASE, "ref_urls.txt")) if l.strip()] if os.path.exists(os.path.join(BASE, "ref_urls.txt")) else []
    if args[0] == "--idphoto":
        jobs = {tag: ("gpt-image-2-official",
                      f"标准证件照:参考照片中是一位{FACE}。{KEEP} 要求:正面直视镜头、头部端正不倾斜,双肩水平对称,"
                      f"嘴唇自然闭合(原照片微张须闭合),表情自然平和,头部占画面上部约三分之二,"
                      f"专业证件照正面均匀柔光、面部无阴影无过曝,{bg}色背景干净无杂物,穿{cloth},"
                      f"高清真实照片质感,严格保持本人长相,不要过度美颜磨皮。",
                      "1184x1664", refs[:1]) for tag, (bg, cloth) in IDPHOTO.items()}
        for tag, (bg, cloth) in IDPHOTO.items():
            jobs[tag] = (jobs[tag][0], jobs[tag][1].replace("{bg}", bg).replace("{cloth}", cloth),
                         jobs[tag][2], jobs[tag][3])
        run(jobs); sys.exit(0)
    scene = args[0]
    models = args[1:] or ["gpt-image-2-official", "seedream-4-5", "seedream-5-0-pro"]
    jobs = {f"{scene}_{m}": (m, f"参考照片中的是一位{FACE}。{KEEP} 场景:{SCENES[scene]}。", "3:4", refs[:1])
            for m in models}
    run(jobs)
