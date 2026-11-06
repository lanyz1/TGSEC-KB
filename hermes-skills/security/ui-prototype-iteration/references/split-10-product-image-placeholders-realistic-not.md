## Product image placeholders (realistic, not glyphs)
- Emoji AND decorative glyph chars (⌁◈✳▦✎) read as slop — user asked to replace them ("实际场景里面这个是商品的实际主图")
- Draw one small inline SVG product illustration per demo SKU (keyboard: rect + keycap strokes; speaker: rect + circles; cable: USB head + line; mouse: rounded rect + scroll line; humidifier: cylinder + water lines; stand: shelf shape), stroke `#9AA0A8`, `stroke-width:1.6–1.8`, `viewBox="0 0 48 48"`, sized by container via CSS (`.thumb svg{width:58%;height:58%}`)
- Sizes: list thumbnails 48–52px (user rejected 36px as too small), detail page main image 72px (`pthumb-lg`) with title/spec/SKU on separate lines
- Swap to real `<img>` later without layout changes

