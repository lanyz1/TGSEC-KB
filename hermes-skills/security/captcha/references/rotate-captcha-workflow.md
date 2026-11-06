# Rotate Captcha Workflow (RC4 角度提交)

> 同源关联：本 reference 是 **ccpow guard 多策略 WAF** 的 rotate 策略（`_ok8_`）。同一 `_guard` 后端还有 slide/click/delay_jump 策略，delay_jump（SHA-256 PoW + `_ok2_`）见 `references/ccpow-guard-delayjump-workflow.md`。guardret 的 RC4（key=guard 前 8 字符）两条策略同源，仅 payload 不同（rotate=`str(angle)`，delay_jump=`str(int(guard[22:])*2+15)`）。

旋转验证码（rotate captcha）：圆形图被旋转 φ，求解器需恢复角度并提交。与滑块验证码（缺口距离）不同。信号：`/_guard/rotate.png`、`guard`、`guarddata`、`guardret` cookie。

## Recognition Signals

- Challenge: `GET /_guard/rotate.png` → `Set-Cookie: guard=<8hex><4suffix>`, `guarddata=<16B b64>`
- Submit: `GET /` with `Cookie: guardret=<b64>`
- Success: HTTP `512` + `Set-Cookie: _ok8_=<96B>`（清空 guard/guardret/guardword/guarddata）
- Image: 680x250 RGBA，左半 = 参考照片（中心透明洞），右半 = 被旋转 φ 的圆盘（alpha 遮罩）
- Rotation axis ≈ (170,125)：洞心 == 盘心 == 旋转轴（数值质心验证三点重合）

## 提交加密: RC4（密钥随会话下发）

- key = `guard` cookie 前 8 字符（每次会话轮换）
- ciphertext: `guardret = b64(RC4(str(angle), key))` — 无 IV/无盐/无时间戳，纯对称流，确定性
- KSA: `S[0..255]=i; j=(j+S[i]+key[i%len(key)])%256; swap(S[i],S[j])`
- PRGA: `i=(i+1)%256; j=(j+S[i])%256; swap; out ^= S[(S[i]+S[j])%256]`
- 提交仅 cookie 往返，无轨迹/无指纹/无额外头

## 角度求解（视觉 · G 通道行剖面相关）

- 输入: 挑战图 680x250 RGBA；参考 `profL[y] = mean(G 通道) over opaque 行`
- θ* = argmax Pearson(profL, prof(rotate(R, θ)))
- 粗扫 2° 步进 → 峰值邻域 ±3° 内 0.2° 细化 → top-2 峰
- 候选簇: 峰 ± {0, 1.5, 2.5, 3, 4.5}（容差 ±1~3°）
- 实测: 通关 42.7 = 峰 40.2 + 2.5
- 缺陷: 高相关(0.88~0.93)仍可脱靶；带状对称内容存在 180° 歧义

## 拖动映射与提交串

- `angle = x / (slider.offsetWidth - handle.offsetWidth) * 360`（350-50=300px → 1px=1.2°）
- 提交串 = `parseFloat(overlay.style.transform rotate(θdeg))` → toString

## 通关判定与消费语义

- 成功 = `512` + `Set-Cookie: _ok8_=<96B>`（Max-Age=604800）+ guard 系列 cookie 清空
- 失败 = `200` 挑战页（静默，不消耗挑战 → 同挑战可连续提交候选）
- 成功即消费 → (guarddata, guardret) 对重放死
- `_err = guardok-8|rotate-N`（N 随偏差变化 8/10 实测；仅在缺 guarddata 时出现）

## 混淆器逆向（obfuscator.io）

- self-defending: `Function('return (function(){}).constructor("debugger;")')()` + setInterval 2s
- 关键: `_0x1b052d('init')` 返回函数本身（非调用结果）→ 源码正则检测通过 → 递归陷阱被 try/catch 吞
- 假旋转器（字符串表「旋转器」首尾对消）: `for(x=arr.shift(); x && x!==(arr.pop()+'').replace(/[fkjwhCWBlwwfXhASZ=]/g,''); i++){ i ^= 0x1734a0; }` — 首元 `var _0xody='v2'`；尾元去噪后恰为 'v2' → 首判即假，循环体零次执行；实际只首尾各删一个元素，索引映射 = 字面索引-1（静态分析易误判真旋转）
- 死代码: guardword 解密 → parseInt → 结果未使用
- CDP Debugger attach 后每 2s 数百次暂停风暴；不 attach 完全静默

## 纯协议交付

- Python: 拉挑战（rotate.png + guard/guarddata cookie）→ 视觉求 θ → RC4 加密 → `GET /` 带 guardret cookie → 判 512/_ok8_
- 无需浏览器；RC4 纯 Python 实现约几十行；视觉用 PIL + numpy 做 G 通道行剖面相关
