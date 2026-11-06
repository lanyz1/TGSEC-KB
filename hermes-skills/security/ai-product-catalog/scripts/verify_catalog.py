#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A4 产品图册(catalog.html)无头验证:逐页溢出检测 + 价格条/SKU 重合检测 + 可选 PDF 预览渲染。

实测路径(2026-08-15):browser-use/puppeteer 均不可用时,系统 Chrome headless
--dump-dom + title 注入即可拿到结构化布局检测结果,无需任何 npm 依赖。

用法:
  python verify_catalog.py "C:/Users/xxx/Desktop/产品图册/catalog.html"
  python verify_catalog.py "C:/Users/xxx/Desktop/产品图册/catalog.html" --pdf
  python verify_catalog.py "C:/Users/xxx/Desktop/产品图册/catalog.html" --pages 2,30,31,32 --pdf

输出:总页数 / 溢出页列表(页号、类型、标签、超出 mm)/ 坏图 /
      价格条与 SKU 卡片重合列表(间距 < 0mm)/ 续页分布;
--pdf 时生成 _preview.pdf 并渲染指定页 PNG 到同目录(默认 1,2,末页)。

原理:
  1. 把检测脚本注入副本 _check.html(结果 JSON 写入 document.title)
  2. 临时 http.server 提供页面(file:// 中文路径不稳)
  3. chrome --headless=new --dump-dom --virtual-time-budget=5000 取 DOM
  4. 正则提取 <title>CHECK:{...}</title> 解析

检测项:
  - overflow: 每页最后一个子元素 bottom 是否超出 .page bottom(>1mm 算溢出)
  - overlap:  .pricecards 顶部 vs .skus 卡片底部,间距 <0mm = 重合
              (2026-08-15 事故:SKU 多时主页价格条压到 SKU 框,用户肉眼发现)
  - brokenImgs: 未加载成功的 <img>
  - conts: 所有 SKU 续页的 产品名:行数,核对拆页分布是否符合预期
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

CHECK_SCRIPT = """<script>
window.addEventListener('load', () => { setTimeout(() => {
  try {
    const pages = [...document.querySelectorAll('.page')];
    const overflow = [];
    const overlap = [];
    pages.forEach((pg, i) => {
      const r = pg.getBoundingClientRect();
      const bottom = Math.max(...[...pg.children].map(k => k.getBoundingClientRect().bottom));
      const h2 = pg.querySelector('h2');
      const label = (h2 ? h2.textContent : pg.className).slice(0, 20);
      const mm = +((bottom - r.bottom) / 3.7795).toFixed(1);   // px -> mm (96dpi)
      if (mm > 1) overflow.push({ i: i + 1, kind: pg.className.split(' ')[1] || 'cover', label, mm });
      const skus = pg.querySelector('.skus');
      const cards = pg.querySelector('.pricecards');
      if (skus && cards) {
        const gap = +((cards.getBoundingClientRect().top - skus.getBoundingClientRect().bottom) / 3.7795).toFixed(1);
        if (gap < 0) overlap.push({ i: i + 1, label, gap });
      }
    });
    const imgs = [...document.images].filter(im => !im.complete || im.naturalWidth === 0);
    const conts = pages.filter(pg => pg.classList.contains('detail-cont'))
                       .map(pg => (pg.querySelector('h2')?.textContent || '') + ':' + pg.querySelectorAll('.sku-row').length);
    document.title = 'CHECK:' + JSON.stringify({ total: pages.length, overflow, overlap,
                     brokenImgs: imgs.map(im => im.getAttribute('src')), conts });
  } catch (e) { document.title = 'CHECKERR:' + e.message; }
}, 1500); });
</script></body>"""


def find_chrome():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    sys.exit("未找到 Chrome,请修改 CHROME_CANDIDATES")


def serve(dirpath, port):
    import http.server
    old = os.getcwd()
    os.chdir(dirpath)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.chdir(old)
    return srv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html", help="catalog.html 绝对路径")
    ap.add_argument("--pdf", action="store_true", help="额外生成 _preview.pdf 并渲染 PNG")
    ap.add_argument("--pages", default="", help="渲染哪些页(1-based,逗号分隔;默认 1,2,末页)")
    ap.add_argument("--port", type=int, default=8799)
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(args.html))
    src = io.open(args.html, encoding="utf-8").read()
    check_path = os.path.join(base, "_check.html")
    io.open(check_path, "w", encoding="utf-8").write(src.replace("</body>", CHECK_SCRIPT, 1))

    chrome = find_chrome()
    ud = os.path.join(tempfile.gettempdir(), "chrome-hl-cat")
    srv = serve(base, args.port)
    try:
        url = f"http://127.0.0.1:{args.port}/_check.html"
        dom = subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
             "--user-data-dir=" + ud, "--dump-dom", "--virtual-time-budget=5000", url],
            capture_output=True, text=True, timeout=90).stdout
    finally:
        srv.shutdown()

    m = re.search(r"<title>(CHECK[^<]*)</title>", dom)
    if not m:
        sys.exit("未拿到检测结果(页面 JS 报错?):" + dom[:300])
    res = json.loads(m.group(1).replace("CHECK:", ""))

    print(f"总页数:{res['total']}  溢出:{len(res['overflow'])}  重合:{len(res['overlap'])}  坏图:{len(res['brokenImgs'])}")
    for o in res["overflow"]:
        print(f"  溢出 页{o['i']} [{o['kind']}] {o['label']} 超出{o['mm']}mm")
    for o in res["overlap"]:
        print(f"  重合 页{o['i']} {o['label']} 价格条- SKU 间距 {o['gap']}mm(<0 = 压到)")
    for im in res["brokenImgs"]:
        print("  坏图:", im)
    if res.get("conts"):
        print("  续页分布:", "; ".join(res["conts"]))

    if args.pdf:
        pdf = os.path.join(base, "_preview.pdf")
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
             "--no-pdf-header-footer", "--user-data-dir=" + ud + "2",
             f"--print-to-pdf={pdf}",
             f"http://127.0.0.1:{args.port}/catalog.html"],
            capture_output=True, timeout=120)
        try:
            import fitz
            doc = fitz.open(pdf)
            print(f"PDF {len(doc)} 页")
            want = [int(x) for x in args.pages.split(",") if x.strip()] if args.pages else []
            want = want or sorted({1, 2, len(doc)})
            for n in want:
                if 1 <= n <= len(doc):
                    pix = doc[n - 1].get_pixmap(dpi=95)
                    p = os.path.join(base, f"_preview_p{n}.png")
                    pix.save(p)
                    print("渲染:", p)
        except ImportError:
            print("提示:安装 PyMuPDF 后 --pdf 才能渲染预览图")

    os.remove(check_path)


if __name__ == "__main__":
    main()
