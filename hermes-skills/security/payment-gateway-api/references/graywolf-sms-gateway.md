# GrayWolf 短信网关接口速查

## 接口（Server: GrayWolf/5.0，XML 响应）
- 余额查询: `/1.dox`
- 状态回执: `/5.dox`
- 获取上行短信(MO): `/6.dox`（MessageID=FetchMOAck）
- 发送短信: `/14.dox`
- 未知 `.dox` 路径会被路由到余额查询接口（无法靠枚举探测注册/管理接口）

## 发送短信参数（GET）
```
UserName / PassWord          # 认证
Caller                       # 主叫号码（默认 85228828198 或账户 calling_number）
Callee                       # 被叫号码
CallerAddrTon / CallerAddrNpi = 1
CalleeAddrTon / CalleeAddrNpi = 1
CharSet                      # 0=GBK 1=UTF-8
DCS                          # 0=ASCII 8=UCS2
Text                         # 内容（url 编码）
```

## 状态码（Status）
- `0` = 成功
- `1` = 登录错误（用户名/密码鉴权错误）
- `2` = 登录错误（IP 地址错误）
- `3` = 登录错误（**账号被禁用**）
- `4` = 登录错误（登录接口数量过多）

## 关键陷阱
- 批量验证账户是否可用：并发请求 `/1.dox?UserName=X&PassWord=Y`，看 `<Status>`。全部 Status=3 = 上游通道整体死亡。
- Status=3 是供应商侧禁用（欠费/违规），平台侧无法恢复；"换网关"需要新供应商凭据，数据库/代码里搜不到就是没有备用通道，别在平台侧建户分额度白费功夫。
