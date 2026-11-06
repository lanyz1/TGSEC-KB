# 后会无期4.15.exe 校验链定位(2026-08-09 实测,含反汇编修正)

场景: 真实卡密已绑定本机可登录,但重放成功响应(54B)被拒「非法数据001」。目标 = 找到客户端校验什么数据。

## ⚠️ 最终结论(反汇编证实)
**「非法数据001」= 数组越界错误提示,不是验证失败提示!** 定位链上各函数反汇编后:
- `0x4dc290` = **数组/集合索引范围检查**(`mov edx,[esp+4]; cmp [ecx+0x198]; cmp [ecx+0x19c]`; 非0=索引在范围内)— 不是校验!
- `0x4e1dc0` = **通用数组访问封装**(0x4dc290 检查失败 → 设「非法数据001」文本)
- `0x4dc090` = **文本设置函数**(ret 0x18 六参数,eax 判断 `cmp eax,1`)
- 完整链: `0x4da980`(响应处理)→ `0x4dae70`(通用函数)→ `0x4e1dc0` → `0x4dc090` → SetWindowTextA
- **成败决定在更高层**(响应绑定校验,防重放)— patch 显示层/数组层到不了成功路径

## 关键地址(主程序 0x400000 内,无独立天盾 DLL)

| 地址 | 真实用途 |
|------|---------|
| `0x4e1dc0` | 数组访问封装(越界→设「非法数据001」) |
| `0x4dc290` | **数组范围检查**(非校验!): `mov edx,[esp+4]; mov eax,[ecx+0x198]; cmp edx,eax; jb fail; mov eax,[ecx+0x19c]; cmp edx,eax; jb ok; fail: xor eax,eax; ret 4` |
| `0x4dc090` | 文本设置函数(参数在寄存器,eax `cmp eax,1`;ret 0x18) |
| `0x4dae70` | 通用函数(0x4da980 调用,参数为指针/句柄) |
| `0x579300` | 间接调用(转发到 SetWindowTextA 链) |

## hook 0x4dc290 的 arg1 dump(4 次调用)

| 次 | arg1(栈 [esp+4]) | 内容 | ret |
|----|------------------|------|-----|
| 1 | `0xd026068` | ASCII `ZKEDD9A119648H894BB35E8D2A86CA55`(卡密明文) | 0 |
| 2 | `0xee4b638` | 结构 `01 00 00 00 0f 00 00 00` + ASCII `Gnimrna1iyy080w`(机器码) | 0 |
| 3 | `0x625f0d` | `01 00 00 00 0f 00 00 00` + 15B 密文 `dc f5 f2 f6 e9 f5 fa aa f2 e2 e2 ab a3 ab ec bc` + GBK 文本(含「检测到调试程序,请关闭」)+ `OD` | 非0(索引在范围) |
| 4 | `0xee4b458` | 同第 2 次(机器码) | 0 |

**关键**: 真实成功登录 vs 重放失败时,0x4dc290 调用模式**完全一样**(1/2/4 次 ret 0,第 3 次非0)→ 它不是成败关键!

## 反调试干扰确认
第 3 次 arg1 的 GBK 文本区含 `bc ec b2 e2 b5 bd` = 「检测到调试程序」— **frida 注入本身触发天盾反调试**,会污染测试状态。之前 frida_redirect(短时单点)成功是因为注入时机/方式未触发。

## patch 实验结论(全部失败,但排除了一堆错误路径)
1. patch 0x4dc290 返回 1 → 「非法数据001」仍出现(0x4da980 有另一路径直接调 0x4dc090)
2. patch 0x4e1dc0 开头 `C3`(ret) → 仍出现(同 1)
3. Interceptor.replace 0x4dc090(arg1==0x86 跳过)→ **无限递归崩溃**(orig NativeFunction 指向替换后代码)→ 程序退出
4. Memory.patchCode 改字节(写 C3)验证: dump 地址确认 `c3` 开头 → patch 生效但解决不了根本
- **教训**: 防重放校验在更高层,显示层 patch 无效;且 patch 后数据结构错误继续 → 崩溃退出(不是进主界面)

## 调用栈样本(FUZZY backtracer)
```
SetWindowTextA 调用链: 0x56d78e <- 0x4dd102 <- 0x4d991d <- 0x4dc090 <- 0x4e1dee <- ...
0x4dc290 调用链:        0x4e1dd7 <- 0x405a67 <- 0x40581a <- 0x405842 <- 0x4db2fa <- 0x4e18c0 <- ...
0x4dc090 直接调用链(另一路径): 0x56d78e <- 0x4dd102 <- 0x4d991d <- 0x4dc090 <- 0x4da984 <- 0x405909 <- 0x4e1bb5 <- 0x40594e <- 0x4e18c0
```

## 复现命令
```bash
# 1. 重启程序到登录窗口,拿 PID
powershell "Get-Process | Where-Object {$_.ProcessName -like '*4.15*'} | Stop-Process -Force; Start-Process 'C:\Users\Administrator\Desktop\后会无期4.15.exe' -WorkingDirectory 'C:\Users\Administrator\Desktop'"
# 2. 启动 fakeserver8(重放模式,测防重放)或 fakeserver7(转发真实)
# 3. hook_arg1.py: hook 0x4dc290 dump arg1(含 connect 重定向)
# 4. drive2.py 点登陆 → 看 arg1 dump + ret
# 5. 反汇编确认函数真实逻辑: dump_code.py(rpc dump)→ capstone 反汇编(分块,dump 上限 8KB/次)
```
