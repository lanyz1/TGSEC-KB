# -*- coding: utf-8 -*-
"""批量 AI 产品场景图生成 (gpt-image-2 via apimart 异步任务) — 3 并发/断点续跑/大图压缩
用法: 改 SRC(商品xlsx)/OUT_DIR/prompt 模板, export APIMART_KEY=sk-xxx 后运行
输出: OUT_DIR/NN_sku.png; 进度写 OUT_DIR 上级 生成日志.txt
"""
import base64, io, json, os, re, time, urllib.request, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "https://apimart.ai/v1/images/generations"
TASK_API = "https://apimart.ai/v1/tasks/"
KEY = os.environ.get("APIMART_KEY", "sk-REPLACE-ME")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

SRC = r"C:\path\to\素材商品批量上架.xlsx"      # 商品 xlsx: 列0标题 列2分类 列5SKU明细 列6主图路径
OUT_DIR = r"C:\path\to\产品图册\images"        # 输出目录(已存在>50KB文件自动跳过=断点续跑)
LOG = os.path.join(os.path.dirname(OUT_DIR), "生成日志.txt")
COMPRESS_KB = 500      # 素材图超过该阈值先压缩(PIL thumbnail 1024 + JPEG q82), 否则 apimart 413
MAX_WORKERS = 3        # 实测并行不排队, 3~5 安全
os.makedirs(OUT_DIR, exist_ok=True)
_lock = threading.Lock()

def log(msg):
    with _lock:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(msg, flush=True)

def post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Authorization", f"Bearer {KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)          # 不带 UA → 403 Cloudflare 1010
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)

def get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {KEY}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

import openpyxl
wb = openpyxl.load_workbook(SRC, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
items = []
for r in rows[1:]:
    if not r[0]:
        continue
    cat = str(r[2] or "")
    img_path = str(r[6] or "").split(";")[0].split(",")[0].strip()
    if not os.path.exists(img_path):
        for ext in [".jpg", ".png", ".webp"]:
            if os.path.exists(img_path + ext):
                img_path += ext
                break
    sku = ""
    m = re.search(r"\|([A-Za-z0-9\-_]+)\|", str(r[5] or ""))
    if m:
        sku = m.group(1)
    items.append({"cat": cat, "img": img_path, "sku": sku or f"item{len(items)+1:02d}"})

# 按品类给不同场景 prompt(整机=科技感办公桌, 耗材=打印机旁工位)
PROMPT_MACHINE = ("Professional product photography: place this exact 3D printer product on a modern minimalist tech desk "
                  "in a bright futuristic office studio, soft studio lighting, shallow depth of field, "
                  "keep the product design exactly the same, photorealistic, ultra detailed")
PROMPT_FILAMENT = ("Professional product photography: place this exact 3D printer filament spool on a clean modern desk "
                   "beside a 3D printer in a bright futuristic tech studio, soft lighting, "
                   "keep the product design exactly the same, photorealistic, ultra detailed")

def gen_one(idx, it):
    out_name = f"{idx+1:02d}_{it['sku']}.png"
    out_path = os.path.join(OUT_DIR, out_name)
    if os.path.exists(out_path) and os.path.getsize(out_path) > 50000:
        log(f"[跳过] {idx+1}/{len(items)} {it['sku']} 已存在")
        return "skip"
    if not it["img"] or not os.path.exists(it["img"]):
        log(f"[无图] {idx+1}/{len(items)} {it['sku']}")
        return "fail"
    raw = open(it["img"], "rb").read()
    if len(raw) > COMPRESS_KB * 1024:          # 413 预防: 大图先压缩
        try:
            im = __import__("PIL.Image", fromlist=["Image"]).Image.open(io.BytesIO(raw))
            im.thumbnail((1024, 1024))
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=82)
            raw = buf.getvalue()
            log(f"[压缩] {idx+1} {it['sku']} {len(raw)//1024}KB")
        except Exception as e:
            log(f"[压缩失败] {idx+1} {it['sku']}: {str(e)[:80]}")
    b64 = base64.b64encode(raw).decode()
    prompt = PROMPT_MACHINE if "整机" in it["cat"] else PROMPT_FILAMENT
    payload = {"model": "gpt-image-2", "prompt": prompt, "image_urls": [f"data:image/jpeg;base64,{b64}"], "size": "1024x1024", "n": 1}
    for attempt in range(3):
        try:
            d = post(API, payload)
            tid = d.get("data", [{}])[0].get("task_id")
            if not tid:
                raise RuntimeError(f"无task_id {json.dumps(d, ensure_ascii=False)[:150]}")
            for _ in range(50):                 # 最长 ~7 分钟
                time.sleep(8)
                st = get(TASK_API + tid)["data"]["status"]
                if st == "completed":
                    url = get(TASK_API + tid)["data"]["result"]["images"][0]["url"][0]
                    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90).read()
                    if len(data) > 50000:
                        open(out_path, "wb").write(data)
                        log(f"[完成] {idx+1}/{len(items)} {it['sku']} ({len(data)//1024}KB)")
                        return "ok"
                    raise RuntimeError("图片数据过小")
                if st in ("failed", "error"):
                    raise RuntimeError(f"任务失败 {st}")
        except Exception as e:
            log(f"[重试{attempt+1}] {idx+1} {it['sku']}: {str(e)[:100]}")
            time.sleep(6)
    log(f"[失败] {idx+1}/{len(items)} {it['sku']}")
    return "fail"

log(f"== 批量生图开始: {len(items)} 张, {MAX_WORKERS} 并发 ==")
from collections import Counter
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
    futs = [ex.submit(gen_one, i, it) for i, it in enumerate(items)]
    results = [f.result() for f in as_completed(futs)]
log(f"== 全部结束: {dict(Counter(results))} ==")
