#!/usr/bin/env python3
"""APIMart 多模型出图跑分:并行提交 -> 统一轮询 -> 下载对比。

用法:
    python3 poc_gen.py <scenario> [size] [resolution] [max_models]
    scenario: 预置提示词键名(见 SCENARIOS),可加 --prompt "..." 自定义
前置:
    - 同目录 .apimart_key 文件存 key(600 权限)
    - 本机需 v2rayN 代理 127.0.0.1:10808(直连 api.apimart.ai 不通时)
输出: out/{scenario}_{model}_{i}.png;控制台打印每模型 耗时/cost/credits
"""
import requests, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(HERE, ".apimart_key")).read().strip()
API = "https://api.apimart.ai/v1"
PROXY = {"http": "http://127.0.0.1:10808", "https": "http://127.0.0.1:10808"}
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

SCENARIOS = {
    # 婚纱写真(人像类,选型主场景)
    "wedding": ("专业婚纱摄影照片:一对年轻中国情侣,新娘穿白色拖尾婚纱,新郎穿黑色西装,"
                "站在海边悬崖草坪,日落金色逆光,花艺拱门背景,电影感色调,细节真实,肤质自然,构图大气,超高清", "3:4"),
    # COD 商品素材
    "product": ("高端男士机械手表产品图,白底,专业电商主图,细节锐利,影棚布光,微距质感,商业广告摄影", "1:1"),
    # AI 发型试戴
    "hair": ("时尚发型设计展示:年轻亚洲女性,精致层次短发,栗棕色染发,沙龙摄影棚灯光,"
             "发丝细节清晰,背景干净渐变,商业美发广告", "3:4"),
}

DEFAULT_MODELS = [
    "seedream-4-5", "seedream-5-0-pro", "seedream-5-0-lite",
    "gpt-image-2-official", "qwen-image-3.0", "gemini-3.1-flash-image-preview",
    "wan2.7-image", "flux-2-pro", "imagen-4.0-apimart", "grok-imagine-image",
]


def submit(m, prompt, scenario):
    """提交任务,兼容 data 为数组或对象两种响应形状"""
    payload = {"model": m["model"], "prompt": prompt,
               "size": m.get("size"), "resolution": m.get("resolution", "2K"), "n": 1}
    payload = {k: v for k, v in payload.items() if v is not None}
    if m.get("image_urls"):
        payload["image_urls"] = m["image_urls"]
    try:
        r = requests.post(f"{API}/images/generations", json=payload, headers=H, proxies=PROXY, timeout=60)
        d = r.json()
        data = d.get("data")
        task_id = None
        if isinstance(data, list) and data:
            task_id = data[0].get("task_id")
        elif isinstance(data, dict):
            task_id = data.get("task_id")
        if not task_id:
            return {"ok": False, "err": f"no task_id: {str(d)[:250]}"}
        return {"ok": True, "task_id": task_id}
    except Exception as e:
        return {"ok": False, "err": str(e)}


def check(task_id):
    try:
        r = requests.get(f"{API}/tasks/{task_id}?language=zh", headers=H, proxies=PROXY, timeout=30)
        d = r.json()
        data = d.get("data", {})
        st = data.get("status")
        if st == "completed":
            imgs = data.get("result", {}).get("images", []) or []
            urls = []
            for it in imgs:
                u = it.get("url")
                if isinstance(u, list):
                    urls.extend(u)
                elif u:
                    urls.append(u)
            return {"state": "done", "urls": urls, "cost": data.get("cost"),
                    "credits": data.get("credits_cost")}
        if st in ("failed", "error", "cancelled"):
            return {"state": "err", "err": f"{st} {str(d)[:300]}"}
        return {"state": "pending"}
    except Exception as e:
        return {"state": "pending", "note": str(e)}


def download(url, path):
    for proxy in (PROXY, None):
        try:
            r = requests.get(url, proxies=proxy, timeout=120)
            if r.status_code == 200:
                open(path, "wb").write(r.content)
                return True
        except Exception:
            continue
    return False


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "wedding"
    size = sys.argv[2] if len(sys.argv) > 2 else None
    reso = sys.argv[3] if len(sys.argv) > 3 else "2K"
    names = sys.argv[4].split(",") if len(sys.argv) > 4 else None
    if scenario in SCENARIOS and "--prompt" not in sys.argv:
        prompt, default_size = SCENARIOS[scenario]
        size = size or default_size
    else:
        prompt = " ".join(sys.argv[sys.argv.index("--prompt") + 1:]) if "--prompt" in sys.argv else "a cat"
        size = size or "1:1"

    mods = [{"model": n, "size": size, "resolution": reso} for n in (names or DEFAULT_MODELS)]
    print(f"[scenario={scenario} size={size} res={reso}] 提交 {len(mods)} 个模型 ...", flush=True)
    pending, done = [], {}
    for m in mods:
        res = submit(m, prompt, scenario)
        if res["ok"]:
            pending.append({"m": m, "task_id": res["task_id"], "t0": time.time()})
            print(f"  OK {m['model']:<38} task_id={res['task_id'][:44]}", flush=True)
        else:
            print(f"  XX {m['model']:<38} {res['err']}", flush=True)

    print("统一轮询中...", flush=True)
    while pending and time.time() - pending[0]["t0"] < 360:
        nxt = []
        for p in pending:
            res = check(p["task_id"])
            if res["state"] == "done":
                done[p["m"]["model"]] = res
                print(f"  OK {p['m']['model']:<38} {int(time.time()-p['t0'])}s "
                      f"cost={res['cost']} credits={res['credits']} imgs={len(res['urls'])}", flush=True)
            elif res["state"] == "err":
                print(f"  XX {p['m']['model']:<38} {res['err']}", flush=True)
            else:
                nxt.append(p)
        pending = nxt
        if pending:
            time.sleep(4)
    for p in pending:
        print(f"  -- 超时 {p['m']['model']} {p['task_id']}", flush=True)

    print("下载结果图...", flush=True)
    ok = 0
    for model, res in done.items():
        for i, u in enumerate(res["urls"]):
            path = os.path.join(OUT, f"{scenario}_{model}_{i}.png")
            if download(u, path):
                ok += 1
                print(f"  OK {model} -> {path} ({os.path.getsize(path)} bytes)", flush=True)
            else:
                print(f"  XX 下载失败 {model} {u}", flush=True)
    print(f"DONE 下载 {ok}/{sum(len(r['urls']) for r in done.values())}")


if __name__ == "__main__":
    main()
