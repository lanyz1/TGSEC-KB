#!/usr/bin/env python3
"""Click a Telegram bot inline button BY TEXT via Telethon; print the edited/new screen.

Usage: python3 tg_bot_click.py <session_path> <bot_username> <button_text> [api_id] [api_hash]

Notes:
  - These bots use single-screen EDIT UIs: old buttons vanish after each press.
    If the button is not found, click '返回' / the main-menu text first, then retry.
  - Re-fetch messages after EVERY click; space clicks ~3-5s (flood limits).
  - Default api_id/hash = Telegram Desktop public pair found in most dumped session bundles.
"""
import asyncio, sys
from telethon import TelegramClient

SESS = sys.argv[1]
BOT = sys.argv[2]
TXT = sys.argv[3]
API_ID = int(sys.argv[4]) if len(sys.argv) > 4 else 2040
API_HASH = sys.argv[5] if len(sys.argv) > 5 else 'b18441a1ff607e10a989891a5462e627'


async def main():
    c = TelegramClient(SESS, API_ID, API_HASH, device_model='MacBook Pro')
    await c.connect()
    try:
        msgs = await c.get_messages(BOT, limit=8)
        for m in msgs:
            if not m.buttons:
                continue
            for i, row in enumerate(m.buttons):
                for j, b in enumerate(row):
                    if TXT in (b.text or ''):
                        print(f'clicking [{b.text}] on msg {m.id}')
                        await m.click(i, j)
                        await asyncio.sleep(4)
                        nm = (await c.get_messages(BOT, limit=1))[0]
                        print('reply:', (nm.text or '')[:800].replace('\n', ' | '))
                        if nm.buttons:
                            for r in nm.buttons:
                                print('  btns:', [x.text for x in r])
                        return
        print('button not found in last 8 msgs:', TXT)
    finally:
        await c.disconnect()


asyncio.run(main())
