# 2026-08-13 客服四波: 角色权限页 UI + 新增客服 + 翻译批量插入定稿法

## ★ 翻译批量插入定稿法(本次两次事故后的最终正确姿势)

在 `lib/translations.ts` 用 python 脚本批量插 6 语言键时,按此流程,否则必翻车:

### 事故复盘(两次)
1. **语言错位**:值数组按 `[zh,en,es,fr,pt,ru]` 定义,但锚点索引按出现顺序写 → es 区插了英文值。文件实际语言区序是 **es,fr,pt,ru,zh,en**(按行号 998,3114,5232,7349,10094,13167 递增)。
2. **缺逗号**:插入块 `f'  {kv}...\n'` 行尾没加 `,` → TS1005 全文件报错。
3. **重复插入**:第一次脚本锚点匹配到已插入区(如 fr/en 的 `chat.tab.support` 值都是 "Support")→ 二次插入造成重复键;`src.replace` 单发匹配也容易打错位置。
4. 修复方式:整文件 `git checkout <上一commit>^ -- lib/translations.ts` 回滚,修正脚本重做(不要手改已破坏的文件)。

### 定稿脚本模式
```python
# 值数组固定按 [zh, en, es, fr, pt, ru] 定义
KEYS = {"k1": ["中文", "English", "Español", "Français", "Português", "Русский"], ...}
kv = lambda k, v: json.dumps(k, ensure_ascii=False) + ": " + json.dumps(v, ensure_ascii=False)
# 锚点用"该语言实际存在的值"(可能被 LanguageSync 机翻改过, 先 grep 实际值!),
# 每锚点显式带 KEYS 索引: es→2, fr→3, pt→4, ru→5, zh→0, en→1
anchors = [('"anchor.key": "es值"', 2), ..., ('"anchor.key": "en值"', 1)]
# 收集所有 (pos, lang_idx) → 按 pos 从大到小排序 → 逐处插入(从后往前避免偏移)
# 插入块每行尾带逗号: f'  {kv(k, v[lang_idx])},\n'
```
### 插入后强制验证(每条必做)
- `grep -c '"新键"' lib/translations.ts` 每键必须 = 6(多了是重复,少了是漏)
- 抽查每语言区值正确(用脚本打印 6 处值,确认 es 区是 es 值)
- `npx tsc --noEmit` 全量必须 EXIT 0

## 角色权限页 UI 方案 A(用户拍板)
- 员工卡片:16px 圆角白卡 + 渐变头像(按角色配色 ops蓝/finance橙/risk红/logistics青/service紫/arbitration粉/root黑)+ 姓名/邮箱 + 状态徽章(值班中绿/已禁用红/仅客服蓝)
- 权限胶囊:选中 = 蓝底白字,未选 = 灰边;仅客服开启时胶囊区 opacity .45 + pointerEvents none
- 仅客服开关:`.perm-switch` Apple 绿 toggle(globals.css, 40×24, checked 绿 #34C759)
- root 卡:黑徽章"超级管理员 · 全部权限" + 保存禁用
- 用户流程:先做 HTML 多方案预览(D:\跨境商城\会话产物\)用系统 Chrome 挑,选定后落码

## 新增客服功能(仅 root)
- API `POST /api/admin/staffs`:requireRole admin + email===ROOT_EMAIL;body={email,password,displayName,supportNickname?,isAgentOnly?};校验邮箱格式/唯一、密码≥8、名字非空;hashPassword 存;isAgentOnly 默认 true 且 permissionsJson=[];appendOperationLog;invalidateAdminPermCache
- 前端 AdminPermissionsManager:isRoot 时右上角"＋ 新增客服"按钮 → 弹窗(邮箱/密码/名字/昵称/仅客服开关)→ 成功 router.refresh() 重拉列表
- 创建后新账号登录 entry=/agent(仅客服直达工作台)

## ★ 保存成功提示必须走翻译键
API 返回的中文 message(如"已更新 xxx 的权限。")放无 data-i18n 的 div 会被 LanguageSync 半机翻("已Update...Test")。**成功提示一律 `getTranslation(lang, 键)`,失败才保留后端 result.message**(错误详情重要)。

## puppeteer 填 React 受控 input
直接 `input.value = x; dispatchEvent('input')` **不触发 React onChange**(value tracker)。必须:
```js
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
setter.call(input, v); input.dispatchEvent(new Event("input", { bubbles: true }));
```
否则表单 state 不更新 → 提交空值 → API 400,且弹窗不关(误判为功能 bug)。

## 管理端域名隔离补充
- nginx server_name 已含 admin.qavlixor.com,Cloudflare DNS 已解析(无需再配),证书 OK
- middleware host 守卫:`pathname.startsWith("/admin")` 且 host 非 admin.qavlixor.com/localhost → 404
- matcher 必须**显式含 "/admin" 和 "/seller" 根路径**(`/admin/:path*` 不匹配 `/admin` 本身)→ 否则未登录 /admin 绕过守卫渲染侧边栏+嵌入登录
- PortalShell 加 bare 模式:未登录 admin 只渲染登录页(无侧边栏),AdminLayout `bare={!email}`
- 删除管理端侧栏底部"员工后台"说明卡:PortalShell 渲染行删除,ConsolePortalShell note props 改可选
