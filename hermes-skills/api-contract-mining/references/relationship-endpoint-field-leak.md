# 关系端点泄漏（BOLA）：详情端点抹字段，兄弟端点全量返回

## 模式（可直接套用的检查动作）

同资源族内，**详情端点做字段裁剪、关系/列表端点不做**。看到详情端点把敏感字段置空（`loginName:""`、`mobile:null`）时，**不要下「拿不到这些字段」的判**——先把同族端点枚举齐：

```
<族>/friends            <族>/members      <族>/contacts     <族>/participants
<族>/followers          <族>/subscribers  <族>/staff        <族>/colleagues
+ /add /create /join /invite /search /page /list 子路径
```
端点名从 bundle 的路由表/方法表 grep（见 `references/js-bundle-mining-recipes.md`）。

## 操作配方

1. 拿到**任意低权会话**即可（本条不需要管理员）。
2. **先写后读**：关系写入端点通常只校验「目标对象存在/格式」，不校验「对方同意」也不校验角色 → 写入成功后读列表即得目录。
3. 用返回的**关系字段反推 ID 空间**：目录里的 `deptId` / `parentId` / `agentId` / `ownerId` 再喂回 ID 枚举。
4. 两者是互补的存在性预言机：写入端点对**不存在的 ID 也可能回成功**（此时它不是 oracle），详情端点的 200/404 差才是。
5. 命中后用**第二个低权账号**重复一次（证明不是超管特权），并记录被泄漏的字段清单。

## 实测（opensms.xin，2026-09，V-IM 即时通讯族）

| 请求 | 响应 | 结论 |
|---|---|---|
| `GET /csapi/vim/server/users/{id}` | 200 且有行（= 存在性预言机，全站 ~35 用户），但 `loginName` 恒为空串 | 详情端点作字段裁剪 |
| `POST /csapi/vim/server/friends/add {"friendId":"<任意ID>"}` | `{"msg":"添加成功"}`，任意 ID 均成功、连不存在的 ID 也成功 | **无授权、无需对方同意**；非存在性预言机 |
| `GET /csapi/vim/server/friends` | 完整用户对象：`name`(中文名) / `loginName` / `mobile` / `email` / `deptId` | **目录全量泄漏** |

结果：16 个账号整站目录，含 `id=1` = 管理员（`loginName=admin` / 其手机号 / 其邮箱 / `deptId`）与各活跃代理账号（带 `dayliModelTimes` 类计数器 → 直接识别「有业务量、值得优先喷口令」的账号）。

## 同一 BOLA 面通常还挂着三件套

- **自我授权（self-grant）**：`PUT /setting`（自己的对象）成功改写 `canSendMessage` / `canAddFriend` / `showMobile` 等策略位 —— 服务端不校验角色。动作：改 → 重 GET 看是否持久化（持久化才算漏洞，回显不算）。
- **对象 id = 会话 chatId**：建立关系后，聊天/消息族的 `chatId` 可能就等于对方 userId（数字格式校验 + 「窗口已关闭」/「不存在」文案）。用真关系测读/发消息，别用假 id 试。
- **同类写端点的存在性 oracle**：`friends/add` 任意 id 都成功 ⇒ 想判「id 存在」要另找（详情端点状态码）。

## 报告写法

写 **BOLA（对象级授权缺失）**，不写「信息泄漏」：写入端点缺的是**授权**，目录泄漏只是后果。时间线里把「先写后读」的两步都记下，并附被泄漏字段清单与账号数。
