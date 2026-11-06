# telegram.org/faq 原文摘录（2026-08-05 curl 核实）

## 2-Step Verification（锚点 q-how-does-2-step-verification-work）

> Logging in with an SMS code is an industry standard in messaging, but if you're looking for more security or have reasons to doubt your mobile carrier or government, we recommend protecting your cloud chats with an additional password. You can do this in Settings > Privacy and Security > 2-Step Verification. Once enabled, you will need **both an SMS code and a password** to log in. You can also set up a **recovery email address that will help regain access, should you forget your password**. ... You can also set up a **Passkey** to log in without an SMS code at all, using your device's PIN, fingerprint or face scan.

要点：
- 登录必须"短信码 + 密码"两者
- 恢复邮箱的官方定义 = 忘记密码时 regain access，**不负责收短信码**
- Passkey 可免短信，但必须提前在已登录设备设置

## I don't have access to Telegram on any other devices（锚点 i-don-39t-have-access-to-telegram-on-any-other-devices）

> First and foremost, you need to **contact your phone provider, so that they block your old SIM and issue a new one with your number**. Wait till you receive your new SIM with the old number, log in to Telegram, then go to Settings > Devices (or Privacy & Security > Active Sessions) and terminate your Telegram session on the old device.
> ... Note that inactive Telegram accounts self-destruct automatically after a period of time — **18 months being the default setting**.

要点：
- "全设备掉线"的官方唯一路径 = 找运营商补回**同号码** SIM
- 账号自毁默认 **18 个月**（注意：老资料/旧版 FAQ 写 6 个月，已过时）

## I have access to Telegram on another device（锚点 i-have-access-to-telegram-on-another-device）

> Go to Telegram Settings > Privacy and Security and turn on Two-Step Verification. This way the phone number alone will not be enough to log in to your account. Go to Settings > Devices (or Privacy & Security > Active Sessions) and terminate your Telegram session on the old device. ... If you decide to switch to a new phone number, don't forget to go to Settings, tap on your phone number and change your Telegram number to the new one.

## How do I change my phone number?（锚点 q-how-do-i-change-my-phone-number）

> You can change your number in Telegram and keep everything, including all your contacts, messages, and media from the Telegram cloud, as well as all your Secret Chats on all devices. To change your number, go to Settings, then tap on your phone number (just above the username), then 'Change Number'. If you already have a different Telegram account on the target number, you'll need to **delete that account first**.

要点：目标新号上已有 Telegram 账号 → 必须先删那个号上的账号

## 官方支持入口（telegram.org/support 页面核实，2026-08-05）

- 表单字段：Please describe your problem / Your full legal name / Your email / Your phone number → Submit
- 官方支持号：@smstelegram（X/Twitter）
- 登录界面「Didn't get the code?」内也可能有联系支持入口（版本而定）
- 官方对"丢号+无会话"的回复口径 = 找回 SIM；附恢复邮箱 + 用户名 + 设备历史的申诉有极少数成功案例，官方不承诺

## 第三方核实（technobezz.com，2026-08）

> "The phone number is the primary key to every account, so recovery without it depends entirely on whether you have an existing logged-in session... If every session is gone and the number is unreachable, your choices narrow to recovering the SIM or, in the worst case, starting over."

- QR 登录无法用于恢复：只能给已登录的手机授权新桌面/网页会话
- 仍能登录但忘了 2FA 密码且无恢复邮箱：请求重置后需等待 **7 天**，期间任何设备可取消
