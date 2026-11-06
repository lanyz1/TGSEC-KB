## Buyer messages (消息) patterns (verified on 买家消息页)
3-column chat grid (`chat-grid`: 270px session list / chat / 300px context panel, fixed height `calc(100vh-150px)`).
- **Session list**: search box (`cl-search` — inline icon + borderless input) + 全部/未读 seg tabs; `clFilter` filters `.cl-item` by text, `clTab` shows only items containing `.ud` unread badge.
- **Unread dot placement — USER CORRECTION**: red count badge goes in a right column UNDER the timestamp (`.cl-right{flex-direction:column;align-items:flex-end}`: `.tm` then `.ud`), NOT next to the name. Mainstream (WeChat/Taobao) layout; name row stays clean. Clicking a session removes the `.ud` badge (selChat).
- **Real send, not a toast**: `sendMsg()` validates non-empty, appends a `.msg.me` bubble with live HH:MM timestamp, escapes `<` (`v.replace(/</g,'&lt;')`), clears textarea, scrolls `.chat-body` to bottom. Enter sends / Shift+Enter newline via keydown listener on the textarea. Empty input → toast, no bubble.
- **常用语 quick-reply panel**: `.quick-wrap` (relative) wrapping the toolbar icon + `.quick-panel` absolute `bottom:calc(100%+8px)`; `toggleQuick(e,btn)` stopPropagation + exclusive open; `useQuick` inserts item text into textarea; document-level click closes all open panels (same pattern as `.op-menu`).
- **Rich message types in the flow**: buyer image message = `.msg-imgs` of `.mi` thumbnails (116×88, SVG image glyph, caption in `.mt` "14:05 · 包装照片"); seller embedded order card = `.order-card` (mono order# + status pill + product thumb + title + price×qty) clickable → `show('order-detail')`.
- **Read receipts**: seller message `.mt` shows "14:03 · 已读" (buyer read it). AI 摘要 context card retained — it's a mainstream (TikTok Shop) feature, not bragging copy.

