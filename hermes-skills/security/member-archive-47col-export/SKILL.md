---
name: member-archive-47col-export
description: Use when 白标会员库导出后台 47 列玩家档案。
triggers: 47列, 会员档案, 玩家列表导出, 会员表模板, MobileList, 脱库整理, 按表格格式整理
---

# 白标后台会员档案 47 列导出（UG/777club 系 console 口径）

适用:客户给一张后台「玩家列表」导出模板(N 列,含 渠道/销售员/团队 三级归因 + 工资要求),要求把已脱库的会员数据按同格式整理。同族品牌(712win3 / brmt777 / 777club / UG 系)console 列名一致,可直接套用。

## 0. 先做模板归属判定（否则白干）
模板样例往往取自**同族另一品牌实例**。开工前先跑:
1. 模板里的会员 id / 手机 / 账号在 dump 全库查(`grep -rl` 或逐表 dict 查询)——0 命中 = 会员表是另一套实例;
2. 模板的 **渠道/销售员角色ID** 去重后查本库 `OM_Admin.game_channel_account(_temp)`(名册,字段 role_id/username/type/channel_id/remark)——命中率高(实测 97%/98%)= 同一运营团队共享名册,只换会员表;
3. 模板「团队角色ID」通常 0 命中(指向会员侧 id)。
⇒ 按「仅作 N 列格式基准」推进,不要试图让样例行对得上。

## 1. 会员主表与行集
- 行集 = `CD_Account.T_Accounts.AccountID` ∪ `CD_UserDB.T_Role.RoleID`(实测 55,420 + 500 仅角色 = 55,920)。T_Role 独有行账号/国家/注册IP 全空,可用「国家代码非空」筛出纯账号会员。
- 账号列只取 `T_Accounts.AccountName`(勿回退 LoginName/Passport,否则无法区分行集)。同族实例里 AccountName 常是自动生成串 `100bdz####`,而 LoginName 是人名词(beamer/hornby)⇒ 「账号」和「登录名」是两列、勿混。

## 2. 列级映射（实测口径,UG/777club console 47 列）
| 列 | 源 |
|---|---|
| id | T_Accounts.AccountID |
| 手机 / 电话 | T_Accounts.Mobile(两列同源;保持文本,前导 0 不可丢) |
| 国家代码 | T_Accounts.countryCode(BR 等) |
| 锁定 | T_Accounts.Locked → T_Role.Locked → T_UserGameWealth.Locked |
| 登录名 | T_Role.LoginName |
| 游戏类型 | T_Accounts.GmType(玩家=7) |
| 注册时间 / 最后登录IP / 最后登录时间 / 注册IP | T_Accounts.* 缺则 T_Role.* |
| 总存款=总充值 | T_UserCollectData.TotalDeposit |
| 总支出=总提现 | T_UserCollectData.TotalRollOut |
| **资金** | **T_UserGameWealth.Money ÷ 1000**(库内千分之一货币单位) |
| VIP等级 | T_UserVIP.VipLv |
| 系统权限 | T_Role.SystemRight(玩家=0) |
| 父级ID(链) / 父级ID(直接) | T_UserProxyInfo.ParentIds / ParentID(链逗号分隔,末位=直接父级;无上级=0) |
| 邮箱账号 | T_Accounts.MailAccount(常空) |
| 如果内部代理 | T_RoleExpand.IfInnerProxy 缺则 T_UserInnerProxy 命中=1 |
| 提现限制标志 / 游戏限制标志 | T_UserGameWealth.LimitWithdrawFlag / LimitGameFlag |
| 套餐ID / 套餐名称 | T_Accounts.PackageId → OM_MasterDB.T_PackageConfig(0=tp3 1=battle 2=global 3=bharat 4=H5,表仅数行,超字典留空) |
| 等级标签 | T_AccountsTag.LevelTag(常空表) |
| 工资要求ID/需要/当前/添加时间 | CD_UserDB.T_UserWageRequire(按 RoleId 取 AddTime 最新一条) |
| 行号 | 1..N(按 id 升序;原模板是 console 全表序号) |
| 剩余工资要求 | T_RoleExpand.RemainWageRequire(无记录记 0) |
| 用户存款等级 | 推算:TotalDeposit 落 OM_MasterDB.T_UserDepositLevel(首存/百元/五百/千元/三千/五千/万元/三万/五万/十万,区间 [lo,hi)) |
| 省份 | T_Role.ProvinceID → OM_MasterDB.T_SysProvince(同族实例常全 0) |
| 渠道角色ID/备注 | ParentIds 链中 type=3 名册账号 / 其 remark(空则 username) |
| 销售员角色ID/备注 | 链中 type=4 |
| 团队角色ID/备注 | 自身是名册账号则取自身,否则链上最近的 5/6 型账号(从末位往前找) |
| 团队类型 / 父级类型 | 该账号名册 type / 直接父级名册 type(非名册=0) |
| quhao | 由国家代码推导(BR=55 PH=63 IN=91…) |
| 是否为博主 | 会员自身在名册中的 type(type5=blogger<id> 型博主账号,非名册=0) |

## 3. 实测校验（必做,别猜）
- 资金 = Money/1000:拿后台免认证接口/报表页(如 E_ykreport 的 balance=200.00)与库内 Money=200000 双边比对。
- 总存款/总支出:拿后台注入接口(如 MobileList)导出的 3,000 行与 T_UserCollectData 逐行 diff,要求 0 差异。
- 模板自身分布反证:`总存款==总充值`、`总支出==总提现`、`游戏类型全 7`、`系统权限全 0`、`锁定全 0`、`邮箱/等级标签全空`——与库内分布吻合即口径对了。
- 统一输出前把时间列的微秒去掉(`.493000` → 去),数值列转数值型,手机/电话保持文本。

## 4. 坑
- **归因列(渠道/销售员/团队)可能整体稀疏**:T_UserProxyInfo 只有极小比例行有 ParentIds、T_Accounts.ProxyId 常空、10 个库里查不到「会员→代理」绑定表 ⇒ 是数据不存在,不是映射错。判定方法:遍历全库表头,找同时含(roleid/accountid) + (channelid/agentid/parentid/proxyid/spreadid)的表,再统计非零行数。
- 名册账号多半**不是本实例会员**(实测 4,030 名册中仅 22 个在会员集),别指望用 channel_id 反推全量归因。
- 模板里出现「省份=一串手机号」这类串列:是原导出的列错位,按真实字段口径填并在交付说明里写明,别照抄。
- openpyxl `write_only=True` 写 5 万行 × 47 列 ≈ 10MB、几十秒;`freeze_panes='A2'` 在 write_only 下有效;读回时空单元格是 None(不是 ''),统计覆盖率时别把 None 当非空。
- 用 `csv.DictReader(delimiter='\t')` 读 TSV dump:`'0'` 是非空字符串(判「有值」要排除 '0',否则 ParentId 覆盖率会假高)。

## 5. 交付
一份 xlsx:Sheet1 = N 列数据全量;Sheet2 = 列映射与覆盖率(列号/列名/来源表.字段/非空行数/覆盖率/推算说明)。另出 CSV(UTF-8-BOM)+ 交付说明 md(成品规模/逐列覆盖表/关键校验依据/模板归属判定/局限/复现命令)。双份落地:案卷目录 + 桌面。
参考实现:`D:\渗透\712win3-brmt777_20260918\scripts\t530_build47.py`(生成)+ `t531_gen_report.py`(文档)。
