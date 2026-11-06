# 实务例子：EscrowFactory（TRON 担保合约）

一个完整的「只读审计」长什么样。真实数字，供下一个合约照形状走。

对象：`TJWSdudwK7vv6eTFidK2JuuPWhXPezZBsC`（未开源，创建当天即审）

## 第0步：决策树入口

```
拿地址 → TronGrid getcontract
  → bytecode 45532 hex ✓、abi.entrys 59 条 ✓
  → 源码端点试 5 个，全空 ⇒ 判定「未开源」⇒ 走字节码路线
```
**不要因为没源码就降级结论**。字节码 + 链上状态 + 调用仿真三路合起来比源码还硬
（源码能说谎，链上状态不会）。

## 第1步：字节码对差（找出 ABI 漏掉的）

```
dispatcher 提取出 44 个 selector，ABI 只列 29 个 ⇒ 15 个「未标注」
```
逐个判定后**全部是内部函数跳转表**（在字节码里出现 2~10 次，被主流程调用），
字典反查还命中两例：`c45a0155 = factory()`、`5fd19158 = surplusBalance(address)`。

⇒ 结论写「交易所的 ABI 抽取不完整，无后门」。
**这节的价值在于把「15 个未知 selector」从吓人的信号变成一个已排除项** ——
不写它就等于留了个悬案。

（反例警示：若某个 selector 只出现一次且无人调用，那就是真后门，必须逆下去。）

## 第2步：危险 opcode 普查

```
DELEGATECALL 0    SELFDESTRUCT 0    CREATE2 0    CALLCODE 0
CALL 17           CREATE 2          EXTCODEHASH 1
```
- `DELEGATECALL 0` ⇒ **不是代理**（TronScan 却标了 `is_proxy:true` + 实现地址）
  查那个「实现地址」的 `account_name` ⇒ hex 解出 **`CreatedByContract`** ⇒ 占位符，代理说被证伪
- 可升级函数扫一遍（`upgradeTo/setImplementation/setImpl/initialize/init/setService/setFactory`）：**全 0 次**
  ⇒ **合约不可升级**（写进报告的正面结论）
- `CREATE 2` + 6 笔 escrow ⇒ `createEscrow` 会给每笔托管部署子合约（工厂模式）

## 第3步：权限矩阵（全案杀伤力最大的一步）

```
13 个特权函数 × 7 类角色 = 91 次 triggerconstantcontract 仿真（只读、不广播）
```
角色：`owner` / `admin×5` / `partyA` / `partyB` / `service` / `random`

输出长这样（真实结果）：
```
             转走USDT          提盈余         自封admin  暂停  改费率  夺所有权  退款流程
owner       ✗5274afe7(过权限!) ✗82b42900     ★过!   ★过!  ★过!  ★过!   ✗82b42900
admin-099980 ✗82b42900        ✗c1ab6dc1     ✗ ... (全部✗)
admin-26892d ✗82b42900        ★过权限         ★过权限→8e78f0cb(退款类也能过)
partyB      ✗82b42900        ★过权限→8e78f0cb(派对可提议/批准退款 ✓设计如此)
random/service ✗ 全部拒绝
```

**读这张表的方式：**
- `82b42900 = Unauthorized()` ⇒ 拦住了
- `5274afe7 = SafeERC20FailedOperation(address)` ⇒ **owner 过了权限，只是 token 层失败**
  ⇒ 这是「owner 能扫走全部资产」的关键证据。**只看「有 revert」会误判成守住了。**
- 其它错误码（`c1ab6dc1`/`8e78f0cb`，ABI 中无）⇒ 过了权限检查、撞业务前置条件

## 第4步：资金取证

```
入金(4笔): 11:35 3.06 + 11:55 0.113 + 12:23 2.00 + 13:02 2.00 = 7.173 USDT
现值: balanceOf(工厂) = 0                       ← ★合约调用才是真相
TronGrid 的 trc20 索引 = 7173000（滞后，会让人误判「钱还在」）
经济模型: feePerDay = 1 USDT/天 vs 单笔入金 2~3 USDT ⇒ 2~3 天吃光本金
```
两个非常容易做错的地方：
1. **出金必须用 `fromAddress=<合约>` 单查** —— `relatedAddress` 以转入为主，会漏出金
2. **索引用 `balanceOf` 校正** —— 索引与合约调用打架时，合约调用赢

**对手方画像（定性的核心）：** 6 笔 escrow 的 `partyA` **全部是 `type=Contract`**，
且都是本工厂 `CREATE` 出来的（余额 0）；4 笔入金也来自这些自造合约。
→ **自成交刷量**：链上那个「活跃的托管服务」是左手倒右手搭出来的。

## 第5步：报告形状

```
合约定性 → 访问控制审计（矩阵表）→ 风险发现 H1..H6 → 明确排除项 → 结论 → 复现资料
```
本次 H 系列（注意：**没有一个是代码漏洞**）：
```
H1 单点中心化: owner = 单 EOA，能 transferAsset 扫空 + setAdmin + 夺权，无时间锁无多签
H2 运营方可 recoverSurplus 提「盈余」（口径由合约方定义）
H3 费率陷阱: 日租 1 USDT vs 入金 2~3 USDT
H4 自成交伪造活跃度（partyA 全是自造合约）
H5 资金已 100% 转出（入 7.173，现 0）
H6 托管标的非标准 TRC20（无 symbol/decimals）
```
明确排除项（写出来同样重要）：
```
越权调用特权函数 无 | 隐藏后门 selector 无 | 可升级/可替换实现 无 | 自毁 无
重入 有 ReentrancyGuard | 暂停开关 受控 | 代理模式 否
```
结论一句话：**「代码没洞，风险在人」** —— 再列证据。

## 这个例子教的三条通用规律

1. **大部分链上「合约项目」的风险不是代码漏洞，而是治理/经济模型的坑。**
   单点 owner + 能扫资产 + 无时间锁，比任何重入都致命。报告要分「代码」与「治理」两栏。
2. **可证伪的结论和确认的结论一样值钱。** 把「不是代理」「不可升级」「无越权」写清楚，
   能让下一个审的人不重走。
3. **入金量小 + 日租金高 + 对手方是自造合约** —— 这三条同时出现，基本可定性为
   展示型/诱饵型托管。但要克制到结构证据为止，别说成诈骗（那需要受害人侧证据）。
