#!/usr/bin/env python3
"""N 张验证码图 → 一张带行号的纵向联系表，供一次视觉调用读全。

用法:
  python3 captcha_contact_sheet.py out.png cap1.png cap2.png ... [--scale 6] [--label-from 1]

要点（见 SKILL.md §2）：
  - 先把每张图放大再拼，主字符才够大（默认 6x）。
  - 行号画在行首（红色），读码时按行号回报，避免错位。
  - 排版/行高/宽度自适应，不依赖特定验证码尺寸。
"""
import sys
from PIL import Image, ImageDraw


def main():
    args = list(sys.argv[1:])
    scale, label_from = 6, 1
    files = []
    i = 0
    while i < len(args):
        if args[i] == "--scale":
            scale = float(args[i + 1]); i += 2
        elif args[i] == "--label-from":
            label_from = int(args[i + 1]); i += 2
        else:
            files.append(args[i]); i += 1
    if len(files) < 2:
        print(__doc__); sys.exit(2)
    out, files = files[0], files[1:]

    imgs = [Image.open(f).convert("RGB") for f in files]
    imgs = [im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
            for im in imgs]
    lab_w, pad = 110, 12
    W = max(im.width for im in imgs) + lab_w + pad * 2
    H = sum(im.height + pad for im in imgs) + pad
    sheet = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(sheet)
    y = pad
    for idx, im in enumerate(imgs):
        d.text((pad, y + im.height // 2 - 10), "#%d" % (idx + label_from), fill=(200, 0, 0))
        sheet.paste(im, (pad + lab_w, y))
        y += im.height + pad
    sheet.save(out)
    print("wrote %s  %dx%d  rows=%d" % (out, sheet.width, sheet.height, len(imgs)))


if __name__ == "__main__":
    main()
