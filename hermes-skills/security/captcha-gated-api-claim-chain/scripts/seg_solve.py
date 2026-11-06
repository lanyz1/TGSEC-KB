#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seg_solve.py — 离线解「图标网格」挑战:顶部目标图标 vs 下方 N×N 网格,按【形状】匹配。
服务端把颜色随机化 ⇒ 只能比形状(同形目标/答案格尺寸朝向一致、仅配色不同)。纯 PIL+numpy,无 ML。
输出: BEST=<0基格序号或None> SCORES=[...] META={...}   (None = 置信不足, 回退人工读图)
用法: python3 seg_solve.py <png> [grid_size]
"""
import sys


def load(p):
    import numpy as np
    from PIL import Image
    return np.asarray(Image.open(p).convert("RGB")).astype("int16")


def bands(flag, min_gap=4, min_len=6):
    """把 1D 布尔序列切成连续段 [(start,end)] —— 行/列投影定位用"""
    out, s, gap = [], None, 0
    for i, v in enumerate(flag):
        if v:
            if s is None:
                s = i
            gap = 0
        else:
            if s is not None:
                gap += 1
                if gap >= min_gap:
                    e = i - gap + 1
                    if e - s >= min_len:
                        out.append((s, e))
                    s = None
    if s is not None and len(flag) - s >= min_len:
        out.append((s, len(flag)))
    return out


def mask_of(a, box, inset=0.16):
    """盒内前景 mask(inset 去掉格子圆角边框), 裁到内容 bbox"""
    import numpy as np
    x0, y0, x1, y1 = box
    h, w = y1 - y0, x1 - x0
    ix, iy = int(w * inset), int(h * inset)
    sub = a[y0 + iy:y1 - iy, x0 + ix:x1 - ix]
    if sub.size == 0:
        return None
    flat = sub.reshape(-1, 3)
    cols, cnt = np.unique(flat, axis=0, return_counts=True)
    bg = cols[cnt.argmax()]
    m = np.abs(sub - bg).sum(2) > 40
    if m.sum() < 30:
        return None
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def norm_pad(m, size=128):
    """★ 保长宽比填充到正方形 —— 填充式归一化会把宽扁形与竖高形压成同形, 冠军差距会被压到 0.01 级"""
    import numpy as np
    from PIL import Image
    h, w = m.shape
    s = float(size) / float(max(h, w))
    nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    arr = np.asarray(Image.fromarray((m * 255).astype("uint8")).resize((nw, nh), Image.BILINEAR)) > 100
    canvas = np.zeros((size, size), bool)
    y0, x0 = (size - nh) // 2, (size - nw) // 2
    canvas[y0:y0 + nh, x0:x0 + nw] = arr
    return canvas


def iou(a, b):
    return float((a & b).sum()) / float(max(1, (a | b).sum()))


def solve(png, grid=9, min_iou=0.70, min_margin=0.10):
    """返回 (答案序号或None, 每格分数, meta)"""
    import numpy as np
    a = load(png)
    cols, cnt = np.unique(a.reshape(-1, 3), axis=0, return_counts=True)
    bg = cols[cnt.argmax()]
    full = np.abs(a - bg).sum(2) > 40
    rb = bands(full.any(1), min_gap=6, min_len=10)
    if not rb:
        return None, [], {"why": "no-bands"}
    top, rest = rb[0], rb[1:]
    n = {4: 2, 9: 3, 16: 4}.get(int(grid), 3)
    if len(rest) < n:
        return None, [], {"why": "rows<%d" % n}
    boxes = []
    for (y0, y1) in rest[:n]:
        cb = bands(full[y0:y1].any(0), min_gap=6, min_len=10)
        if len(cb) < n:
            return None, [], {"why": "cols<%d" % n}
        for (x0, x1) in cb[:n]:
            boxes.append((x0, y0, x1, y1))
    tb = bands(full[top[0]:top[1]].any(0), min_gap=6, min_len=10)
    tboxes = [(x0, top[0], x1, top[1]) for (x0, x1) in tb]
    if not tboxes:
        return None, [], {"why": "no-target"}
    tbox = tboxes[len(tboxes) // 2] if len(tboxes) > 1 else tboxes[0]
    tm = mask_of(a, tbox)
    if tm is None:
        return None, [], {"why": "target-mask"}
    tn = norm_pad(tm)
    sc = []
    for b in boxes:
        m = mask_of(a, b)
        sc.append(iou(tn, norm_pad(m)) if m is not None else 0.0)
    best = int(max(range(len(sc)), key=lambda i: sc[i]))
    srt = sorted(range(len(sc)), key=lambda i: -sc[i])
    margin = sc[srt[0]] - (sc[srt[1]] if len(srt) > 1 else 0.0)
    ok = (sc[best] >= min_iou and margin >= min_margin)
    return (best if ok else None), [round(s, 3) for s in sc], {"boxes": len(boxes), "margin": round(margin, 3)}


if __name__ == "__main__":
    r, sc, meta = solve(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 9)
    print("BEST=%s SCORES=%s META=%s" % (r, sc, meta))
