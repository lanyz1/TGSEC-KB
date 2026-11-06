# 无 vision 工具的代理截图验收 + 像素级规格补充

场景:用户把基准原型交给 Claude Code 等代理重做,代理自报"按 v2/v3 改好了",但用户"感觉不一样"。无 vision 工具(无 vision_analyze)时,用 **OCR + PIL 像素分析**实读截图,和基准逐条对照,产出"铁证"级判定。

## 1. OCR 提取截图文字(rapidocr-onnxruntime)

```python
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()
result, _ = ocr(img_path)      # 每行: (box, text, confidence)
for line in result:
    print(line[1], f"({line[2]:.2f})")
```

## 2. 像素布局分析(PIL 分区平均色)

```python
im = Image.open(img_path).convert('RGB'); w, h = im.size
def avg_region(box):
    px = list(im.crop(box).getdata()); n = len(px)
    return tuple(sum(p[i] for p in px)//n for i in range(3))
left = avg_region((0,0,w//2,h))          # 左半平均色
dark = sum(1 for p in im.getdata() if p[0]<50 and p[1]<50 and p[2]<50)
print(dark/len(px)*100)                   # 深色像素占比
```

判读:
- 黑底品牌区(`#000`)应占版面 ~30%+;截图几乎全浅灰白 + 深色占比 <10% = **品牌区缺失**
- 两栏布局:左半平均色深、右半浅 = 有品牌区+表单卡;三区全浅 = 纯表单单栏
- 截图尺寸接近正方形(620×629) = 只截了局部,让代理重截全屏

## 3. 基准侧文本提取(对照源)

从基准单文件 HTML 提取每个 section 的可见文本:

```python
import re
i = html.find('<section class="view" id="view-login"'); j = html.find('</section>', i)
texts = re.findall(r'>([^<>]{2,80})<', html[i:j])
# 过滤 svg/path/class 开头,输出逐条「基准原文」
```

## 4. 判定规则(关键:分清是谁的问题)

| 证据 | 判定 |
|---|---|
| 自创文案:基准里没有的按钮/链接/元素(如 `Log in to seller center`、`Back to marketplace`) | **代理的问题**(文案逐字写死它还发明 = 没读基准) |
| 布局缺区:黑品牌区无、两栏变单栏 | 代理的问题 |
| 演示数据被换:当前日期/自造数据(销售趋势图横轴出现当天日期) | 代理的问题(基准是固定锚点数据,如 2026-07-31、末端 410) |
| 全部文案一致仅观感差 | **规格缺像素级参数**(见下节)→ 补规格,不是怪代理 |

## 5. 像素级规格补充(规格"描述"≠"代码",三大无声差异)

1. **字体栈**(最大差异源):`-apple-system, BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei", sans-serif` + `-webkit-font-smoothing:antialiased`
2. **全局重置**:`*{box-sizing:border-box;margin:0;padding:0}`、`html,body{height:100%}`、button/input/a 默认值、`svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}`
3. **图标**:内联 SVG stroke-width 1.8,禁图标库/web 字体

对策:基准文件完整 CSS 原样导出为 `Qavlixor-基准-CSS.css`(572 条规则),命令代理 diff 逐字节对齐(它多出来的规则删掉、缺的补上);HTML 结构命令"复制基准区块,只换数据绑定",禁止重写。

## 6. 交付物模板

- `登录页-逐字修正对照表.md`:表列 = 区块 | 基准原文(照抄这个) | 它做的(必须替换),命令"一个字母不许改"
- `登录页-基准HTML.html`:独立可打开的标准答案(完整 CSS + 该 section),代理照抄零发挥空间
- 每完成一项让代理**整页截图回传**,用户转交后 OCR+像素复核,10 秒判定
